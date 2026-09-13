param([switch]$Force)
$ErrorActionPreference='Stop'
$box = Split-Path $PSScriptRoot -Parent
$state = Join-Path $box '.local\setup.json'
$python = Join-Path $box '.local\venv\Scripts\python.exe'
$planDir = Join-Path $box 'irodori-tts\bf16-fallback'
$plan = Join-Path $planDir 'fallback_bf16.plan'
New-Item -ItemType Directory -Force (Join-Path $box 'logs') | Out-Null
Start-Transcript -Path (Join-Path $box 'logs\trt-setup.log') -Append | Out-Null
try {
  if (!(Test-Path $python)) { throw 'CUDA setup is not complete. Run first_setup.bat first.' }
  # The distributed runtime needs a matching exporter as well as TensorRT itself.
  # Do this before downloading packages so a partial source bundle fails clearly.
  $builder = Join-Path $planDir 'fallback_bf16.py'
  $lab = Join-Path $box 'runtime\trt-lab'
  if (!(Test-Path $builder) -or !(Test-Path (Join-Path $lab 'trt_experiment.py'))) {
    throw "TensorRT setup is unavailable in this package: the required plan builder is missing from $planDir. CUDA / PyTorch remains available."
  }
  $gpu = @(Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notmatch 'Parsec|Remote Display|Hyper-V' } | Select-Object -ExpandProperty Name)
  $smi = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
  if (!$smi) { throw 'nvidia-smi.exe was not found. Install the NVIDIA driver first.' }
  $gpu = @(& $smi.Source --query-gpu=name,compute_cap,memory.total --format=csv,noheader)
  if (!$gpu -or (($gpu -join ' ') -notmatch 'NVIDIA|GeForce|Quadro|Tesla')) { throw 'An NVIDIA CUDA GPU is required for TensorRT.' }
  Write-Host "[1/4] GPU detected: $($gpu -join ', ')" -ForegroundColor Green
  & $python -c "import torch; assert torch.cuda.is_available(), 'CUDA PyTorch is required'; assert torch.cuda.is_bf16_supported(), 'This BF16 builder requires a BF16-capable CUDA GPU'; print(torch.cuda.get_device_name())"
  if ($LASTEXITCODE -ne 0) { throw 'GPU/PyTorch does not support this BF16 TensorRT builder. CUDA / PyTorch remains available.' }
  $checkpoint = Join-Path $box 'models\model.safetensors'
  if (!(Test-Path $checkpoint)) { throw "Model not found: $checkpoint. Run first_setup.bat first." }
  $uv = Join-Path $box '.local\bin\uv.exe'
  if (!(Test-Path -LiteralPath $uv -PathType Leaf)) {
    throw 'Project-local uv is missing. Run first_setup.bat first.'
  }
  Write-Host '[2/4] Installing TensorRT Python package (progress is shown)...' -ForegroundColor Cyan
  & $uv pip install --python $python -r (Join-Path $box 'irodori-tts\requirements-trt.txt')
  if ($LASTEXITCODE -ne 0) { throw "TensorRT install failed ($LASTEXITCODE)." }
  Write-Host '[3/4] Building a plan for this exact GPU/model...' -ForegroundColor Cyan
  # Every attempt gets fresh captures and ONNX, so a changed checkpoint cannot
  # accidentally reuse a previous export. Publish only after deserialization.
  $work = Join-Path $box ('work\trt-setup-' + [guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Force $work | Out-Null
  $env:IRODORI_CHECKPOINT = $checkpoint
  $env:IRODORI_TRT_LAB_DIR = $lab
  $env:IRODORI_TRT_WORK_DIR = $work
  $env:IRODORI_TRT_OUTPUT_DIR = $work
  $env:HF_HOME = Join-Path $box '.cache\huggingface'
  & $python (Join-Path $lab 'trt_experiment.py') export
  if ($LASTEXITCODE -ne 0) { throw 'TensorRT input capture / ONNX export failed.' }
  & $python $builder export
  if ($LASTEXITCODE -ne 0) { throw 'BF16 ONNX export failed.' }
  & $python $builder build
  $candidate = Join-Path $work 'fallback_bf16.plan'
  if ($LASTEXITCODE -ne 0 -or !(Test-Path $candidate)) { throw 'TensorRT plan build failed. See logs\trt-setup.log.' }
  Write-Host '[4/4] Verifying TensorRT import and generated plan...' -ForegroundColor Cyan
  & $python -c "import sys, torch, tensorrt as trt; torch.cuda.init(); runtime = trt.Runtime(trt.Logger(trt.Logger.WARNING)); engine = runtime.deserialize_cuda_engine(open(sys.argv[1], 'rb').read()); assert engine is not None, 'Invalid TensorRT engine'; print('TensorRT', trt.__version__)" $candidate
  if ($LASTEXITCODE -ne 0) { throw 'TensorRT verification failed.' }
  Copy-Item -LiteralPath $candidate -Destination $plan -Force
  Write-Host "TensorRT setup complete: $plan" -ForegroundColor Green
} catch {
  Write-Host "TRT SETUP FAILED: $_" -ForegroundColor Red
  exit 1
} finally { try { Stop-Transcript | Out-Null } catch {} }
