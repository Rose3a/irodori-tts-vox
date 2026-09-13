"""Local engine lifecycle; no GPU imports in the desktop process."""
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BACKEND_IDS = {"CPU / PyTorch": "cpu", "CUDA / PyTorch": "cuda",
               "TensorRT": "trt", "Radeon / DirectML": "radeon"}


def checkpoints():
    return sorted(p for p in (ROOT / "models").rglob("*.safetensors")
                  if not p.name.endswith(".speaker.safetensors"))


class EngineManager:
    def __init__(self):
        self.processes = {}
        self.lock = threading.Lock()
        self.closed = False

    def ensure(self, backend, endpoint, checkpoint):
        with self.lock:
            if backend == "TensorRT" and Path(checkpoint).resolve() != (ROOT / "models" / "model.safetensors").resolve():
                raise RuntimeError("TensorRTはmodels/model.safetensors用です。別モデルはCPU/CUDAを選ぶか、対応planを構築してください")
            if self.closed:
                raise RuntimeError("アプリは終了中です")
            try:
                with urlopen(endpoint + "/engine_manifest", timeout=2) as response:
                    manifest = json.load(response)
                if manifest.get("name") != "Irodori (" + BACKEND_IDS[backend] + ")":
                    raise RuntimeError("このポートは別のエンジンが使用中です")
                reported = manifest.get("irodori_checkpoint")
                if reported and Path(reported).resolve() != Path(checkpoint).resolve():
                    raise RuntimeError("接続先のモデルが選択と異なります。エンジンを停止して再読込してください")
                owned = self.processes.get(backend)
                if owned and owned[1] != checkpoint:
                    raise RuntimeError("モデルを変更する前に「起動したエンジンを停止」を押してください")
                return
            except OSError:
                pass
            python = ROOT / ".venv" / "Scripts" / "python.exe"
            if not python.exists():
                raise RuntimeError("setup_venv.batで実行環境を準備してください")
            if not Path(checkpoint).is_file():
                raise RuntimeError("modelsフォルダにモデルを入れて選択してください")
            env = os.environ.copy()
            env["IRODORI_CHECKPOINT"] = checkpoint
            env.pop("IRODORI_BACKEND", None)
            (ROOT / "logs").mkdir(exist_ok=True)
            log_path = ROOT / "logs" / (BACKEND_IDS[backend] + ".log")
            with log_path.open("ab") as log:
                process = subprocess.Popen([str(python), str(ROOT / "wrapper" / "voicevox_engine.py"),
                    "--backend", BACKEND_IDS[backend], "--port", endpoint.rsplit(":", 1)[1],
                    "--embed-dir", str(ROOT / "embeddings"),
                    "--plan", str(ROOT / "bf16-fallback" / "fallback_bf16.plan")],
                    cwd=ROOT, env=env, stdout=log, stderr=log,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.processes[backend] = (process, checkpoint)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline and not self.closed:
            if process.poll() is not None:
                raise RuntimeError(f"起動失敗。ログ: {log_path}")
            try:
                with urlopen(endpoint + "/version", timeout=2):
                    return
            except OSError:
                time.sleep(0.4)
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        raise RuntimeError(f"起動待ちが終了しました。ログ: {log_path}")

    def stop(self):
        with self.lock:
            for process, _ in self.processes.values():
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
            self.processes.clear()
