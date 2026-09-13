"""Download an Irodori HF checkpoint into the box's HF cache.

usage: python fetch_hf_model.py Aratako/Irodori-TTS-v4.1-Small-MF
"""
import os
import sys
from pathlib import Path

BOX = Path(__file__).resolve().parents[1]
os.environ.setdefault("IRODORI_RUNTIME_DIR", str(BOX / "runtime"))
os.environ.setdefault("IRODORI_HF_HOME", str(BOX / ".cache" / "huggingface"))
os.environ.setdefault("HF_HOME", os.environ["IRODORI_HF_HOME"])
sys.path.insert(0, str(BOX / "runtime" / "trt-lab" / "repo"))

from irodori_tts.inference_runtime import download_hf_checkpoint  # noqa: E402


def main() -> int:
    source = sys.argv[1] if len(sys.argv) > 1 else "Aratako/Irodori-TTS-v4.1-Small-MF"
    print(f"[fetch] source={source} hf_home={os.environ['HF_HOME']}", flush=True)
    path = download_hf_checkpoint(source)
    size = Path(path).stat().st_size
    print(f"[fetch] resolved={path} size={size}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
