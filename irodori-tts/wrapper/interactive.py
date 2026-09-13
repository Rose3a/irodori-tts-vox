"""Arrow-key interactive launcher for the Irodori TTS wrapper."""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def choose(title: str, options: list[str]) -> int:
    index = 0
    while True:
        clear_screen()
        print(title)
        print("矢印キーで選択、Enterで決定、Escで終了\n")
        for i, option in enumerate(options):
            print(f" {'➜' if i == index else ' '} {option}")
        if os.name != "nt":
            value = input("選択番号: ").strip()
            if value.isdigit() and 1 <= int(value) <= len(options):
                return int(value) - 1
            continue
        import msvcrt
        key = msvcrt.getwch()
        if key == "\x1b":
            raise KeyboardInterrupt
        if key in ("\x00", "\xe0"):
            key = msvcrt.getwch()
        if key in ("H", "K"):
            index = (index - 1) % len(options)
        elif key in ("P", "M"):
            index = (index + 1) % len(options)
        elif key in ("\r", "\n"):
            return index


def safe_name(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠_-]+", "_", value)
    return value.strip("._") or "no_speaker"


def main() -> int:
    backend_index = choose("推論方式を選択", [
        "torch (CUDAを使うPyTorch)",
        "trt   (TensorRT)",
        "cpu   (CPU / PyTorch)",
    ])
    backend = ("torch", "trt", "torch")[backend_index]
    if backend_index == 2:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from tts_cli import IrodoriTTS, SpeakerCassette, resolve_embed_dirs

    embed_dirs = resolve_embed_dirs()
    cassette = SpeakerCassette(embed_dirs)
    speaker_names = cassette.speakers
    speaker_index = choose("話者を選択", ["(話者なし)"] + speaker_names)
    # Empty string means explicitly no speaker; None means use the default.
    speaker = "" if speaker_index == 0 else speaker_names[speaker_index - 1]

    clear_screen()
    text = input("生成するテキスト: ").strip()
    if not text:
        print("テキストが空なので終了します。")
        input("Enterで終了...")
        return 2

    out_dir = ROOT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_wav = out_dir / f"interactive_{safe_name(speaker or 'no_speaker')}_{stamp}.wav"

    print("\nモデルを読み込み中...")
    started = time.perf_counter()
    tts = IrodoriTTS(backend=backend, embed_dirs=embed_dirs,
                     allow_no_speaker=True)
    result = tts.synthesize(text=text, speaker=speaker, out_wav=out_wav)
    elapsed = time.perf_counter() - started
    print("\n生成完了")
    print(f"  backend : {result['backend']}")
    print(f"  time    : {elapsed:.2f} s (engine {result['engine_wall_s']:.2f} s)")
    print(f"  output  : {out_wav}")
    input("\nEnterで終了...")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nキャンセルしました。")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\n[error] {type(exc).__name__}: {exc}")
        input("Enterで終了...")
        raise SystemExit(1)
