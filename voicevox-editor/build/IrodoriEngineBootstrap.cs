using System;
using System.IO;
using System.Diagnostics;
class EngineBootstrap {
 static int Main(string[] args) {
  try {
   string home = AppDomain.CurrentDomain.BaseDirectory;
   string root = Path.GetFullPath(Path.Combine(home,File.ReadAllText(Path.Combine(home,"irodori-engine-path.txt")).Trim()));
   string box = Directory.GetParent(root).FullName;
   string python = Path.Combine(box,".local","venv","Scripts","python.exe");
   if (!File.Exists(python) || !File.Exists(Path.Combine(box,".local","setup.json"))) {
    Console.Error.WriteLine("Run Irodori VOICEVOX Editor.exe at the ZIP root to complete first setup."); return 2;
   }
   foreach(string arg in args) if (arg.Contains("\"") || arg.Contains("\n")) return 2;
   string command = "\"" + Path.Combine(root,"wrapper","editor_engine.py") + "\"";
   if(args.Length > 0) command += " \"" + string.Join("\" \"", args) + "\"";
   var start = new ProcessStartInfo(python, "-u " + command);
   start.WorkingDirectory=root; start.UseShellExecute=false; start.CreateNoWindow=true;
   start.EnvironmentVariables["PYTHONIOENCODING"]="utf-8";
   start.EnvironmentVariables["PYTHONUTF8"]="1";
   start.EnvironmentVariables["IRODORI_RUNTIME_DIR"]=Path.Combine(box,"runtime");
   start.EnvironmentVariables["IRODORI_HF_HOME"]=Path.Combine(box,".cache","huggingface");
   start.EnvironmentVariables["HF_HOME"]=Path.Combine(box,".cache","huggingface");
   start.EnvironmentVariables["IRODORI_CACHE_DIR"]=Path.Combine(box,".cache","irodori-tts-cache");
   start.EnvironmentVariables["IRODORI_MODEL_DIR"]=Path.Combine(box,"models");
   start.EnvironmentVariables["IRODORI_EMBED_DIR"]=Path.Combine(box,"speakers");
   start.EnvironmentVariables["IRODORI_OUT_DIR"]=Path.Combine(box,"outputs");
   Directory.CreateDirectory(Path.Combine(box,"logs"));
   start.RedirectStandardOutput=true; start.RedirectStandardError=true;
   using(var log = new StreamWriter(Path.Combine(box,"logs","engine-" + Process.GetCurrentProcess().Id + ".log"),true)) {
    log.AutoFlush=true;
    using(var process = new Process()) {
     process.StartInfo=start;
     process.OutputDataReceived += (s,e) => { if(e.Data!=null) { lock(log) log.WriteLine(e.Data); Console.WriteLine(e.Data); } };
     process.ErrorDataReceived += (s,e) => { if(e.Data!=null) { lock(log) log.WriteLine(e.Data); Console.Error.WriteLine(e.Data); } };
     process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine();
     process.WaitForExit(); return process.ExitCode;
    }
   }
  } catch(Exception ex) { Console.Error.WriteLine(ex); return 1; }
 }
}
