[CmdletBinding()]
param(
    [ValidateSet('auto', 'cuda', 'cpu', 'radeon')]
    [string]$Backend = 'auto',
    [switch]$Yes,
    [switch]$KeepFrontend,
    [switch]$KeepCaches,
    [switch]$NoPause,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$box = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$boxPrefix = $box.TrimEnd('\') + '\'

function Get-BoxPath([string]$RelativePath) {
    $path = [IO.Path]::GetFullPath((Join-Path $box $RelativePath))
    if (!$path.StartsWith($boxPrefix, [StringComparison]::OrdinalIgnoreCase) -and $path -ne $box.TrimEnd('\')) {
        throw "Refusing a path outside the project root: $path"
    }
    return $path
}

function Get-ManifestEntry([string]$RelativePath) {
    $path = Get-BoxPath $RelativePath
    $item = Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    $entry = [ordered]@{ path = $RelativePath; fullPath = $path; exists = [bool]$item; kind = if ($item) { if ($item.PSIsContainer) { 'directory' } else { 'file' } } else { $null } }
    if ($item -and !$item.PSIsContainer -and $item.Length -le 1048576 -and $RelativePath -notmatch '(?i)(^|[\/])\.env$') {
        $entry.sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash
        $entry.bytes = $item.Length
    }
    return [pscustomobject]$entry
}

function Get-ActiveProjectSession {
    $hits = [System.Collections.Generic.List[string]]::new()
    $rootNeedle = $box.ToLowerInvariant()
    try {
        foreach ($process in @(Get-CimInstance Win32_Process -ErrorAction Stop)) {
            $name = [string]$process.Name
            $command = [string]$process.CommandLine
            $nameLower = $name.ToLowerInvariant()
            $commandLower = $command.ToLowerInvariant()
            if ($process.ProcessId -eq $PID -or $nameLower -in @('powershell.exe', 'pwsh.exe', 'conhost.exe', 'cmd.exe')) { continue }
            if ($commandLower -match 'rebuild_environment\.ps1') { continue }
            if ($nameLower -eq 'kataribe.exe' -or ($commandLower.Contains($rootNeedle) -and ($nameLower -in @('node.exe', 'nodejs.exe', 'python.exe', 'pythonw.exe', 'electron.exe') -or $commandLower -match 'editor_engine\.py|browser_session\.py|vite'))) {
                $hits.Add("PID $($process.ProcessId): $name $command")
            }
        }
    } catch {
        Write-Warning ("Detailed process command lines were unavailable; using safe name/port checks: " + $_.Exception.Message)
        try {
            foreach ($process in @(Get-Process -Name 'kataribe', 'electron' -ErrorAction SilentlyContinue)) {
                $hits.Add("PID $($process.Id): $($process.ProcessName)")
            }
        } catch { Write-Warning 'Fallback process check was unavailable; port checks still apply.' }
    }
    foreach ($port in @(50125, 5173)) {
        try {
            $connections = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
            if ($connections.Count -gt 0) {
                foreach ($connection in $connections) { $hits.Add("TCP $port listening (PID $($connection.OwningProcess))") }
            }
        } catch {
            throw "Unable to safely query TCP listeners for port ${port}: $($_.Exception.Message)"
        }
    }
    return @($hits | Select-Object -Unique)
}

$deleteRelative = @('.local/venv', 'work/amd-dml-venv', '.local/setup.json')
if (!$KeepFrontend) { $deleteRelative += 'voicevox-editor/node_modules' }
if (!$KeepCaches) { $deleteRelative += '.local/uv-cache' }
$preserveRelative = @('models', 'speakers', 'voicevox-editor/.env', 'voicevox-editor/editor-settings.json', 'irodori-tts', 'voicevox-editor/src', 'tools', 'bat', 'runtime', 'outputs', 'logs', '.local/python', '.local/node')

Write-Host 'Environment rebuild scope:' -ForegroundColor Cyan
Write-Host ('  Project root: ' + $box)
Write-Host '  Delete/rebuild only:'; $deleteRelative | ForEach-Object { Write-Host ('    ' + $_) }
Write-Host '  Always preserve:'; $preserveRelative | ForEach-Object { Write-Host ('    ' + $_) }
Write-Host '  Models and speakers are intentionally retained.'

$active = @(Get-ActiveProjectSession)
if ($active.Count) {
    Write-Host 'REFUSING TO CONTINUE: close the browser/editor session first.' -ForegroundColor Red
    $active | ForEach-Object { Write-Host ('  ' + $_) -ForegroundColor Red }
    exit 2
}

$manifestDir = Get-BoxPath 'backups'; New-Item -ItemType Directory -Force -Path $manifestDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'; $manifestPath = Join-Path $manifestDir "rebuild-environment-$stamp.json"; $suffix = 0
while (Test-Path -LiteralPath $manifestPath) { $suffix++; $manifestPath = Join-Path $manifestDir "rebuild-environment-$stamp-$suffix.json" }
$manifest = [ordered]@{
    createdUtc = [DateTime]::UtcNow.ToString('o'); projectRoot = $box; dryRun = [bool]$DryRun; backend = $Backend
    delete = @($deleteRelative | ForEach-Object { Get-ManifestEntry $_ })
    preserve = @($preserveRelative | ForEach-Object { Get-ManifestEntry $_ })
    controlFiles = @('.local/setup.json', 'voicevox-editor/editor-settings.json', 'voicevox-editor/.env') | ForEach-Object { Get-ManifestEntry $_ }
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host ('Manifest written: ' + $manifestPath)

if ($DryRun) { Write-Host 'DRY RUN: no deletion and no setup command executed.' -ForegroundColor Yellow; exit 0 }
if (!$Yes) {
    $answer = Read-Host 'Proceed with the listed environment cleanup and setup? [y/N]'
    if ($answer -notmatch '^(?i:y|yes)$') { Write-Host 'Cancelled. Nothing was deleted.'; exit 0 }
}
foreach ($relative in $deleteRelative) {
    $path = Get-BoxPath $relative
    if (Test-Path -LiteralPath $path) { Write-Host ('Removing ' + $relative); Remove-Item -LiteralPath $path -Recurse -Force } else { Write-Host ('Missing, skipping ' + $relative) }
}

$setup = Get-BoxPath 'tools/setup.ps1'
Write-Host ('Starting existing setup: tools/setup.ps1 -Backend ' + $Backend) -ForegroundColor Cyan
$setupProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $setup, '-Backend', $Backend) -WorkingDirectory $box -Wait -PassThru
$setupExit = [int]$setupProcess.ExitCode
Write-Host ('Existing setup exit code: ' + $setupExit)
exit $setupExit
