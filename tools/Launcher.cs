using System;
using System.IO;
using System.Diagnostics;
using System.Threading;
class Launcher {
 static int Main(string[] args) {
  string box = AppDomain.CurrentDomain.BaseDirectory;
  bool acquired = false;
  using (var mutex = new Mutex(false, "Local\\IrodoriBox-" + box.ToLowerInvariant().GetHashCode().ToString("X"))) {
   try {
    try { acquired = mutex.WaitOne(0); } catch (AbandonedMutexException) { acquired = true; }
    if (!acquired) return 0;
    var setup = new ProcessStartInfo("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -File \"" + Path.Combine(box,"tools","setup.ps1") + "\"");
    setup.UseShellExecute=false; setup.WorkingDirectory=box;
    using (var process = Process.Start(setup)) { process.WaitForExit(); if (process.ExitCode != 0) { Console.WriteLine("Setup failed. See logs\\first-setup.log. Press Enter to close."); Console.ReadLine(); return 1; } }
    string editor = null;
    foreach (var candidate in new[] {
     Path.Combine(box,"voicevox-editor","dist_electron","win-unpacked","kataribe.exe"),
     Path.Combine(box,"voicevox-editor","dist_electron","kataribe.exe")
    }) if (File.Exists(candidate)) { editor = candidate; break; }
    ProcessStartInfo start;
    if (editor != null) {
     start = new ProcessStartInfo(editor);
     start.WorkingDirectory = Path.GetDirectoryName(editor); start.UseShellExecute=false;
    } else {
     string browser = Path.Combine(box,"open_browser.bat");
     if (!File.Exists(browser)) throw new FileNotFoundException("Editor build and browser launcher were not found", browser);
     start = new ProcessStartInfo(browser);
     start.WorkingDirectory = box; start.UseShellExecute=true;
    }
    using (var process = Process.Start(start)) { }
    return 0;
   } catch (Exception ex) { Console.Error.WriteLine(ex); Console.ReadLine(); return 1; }
   finally { if(acquired) mutex.ReleaseMutex(); }
  }
 }
}
