"""Synthesize real utterances and compare their DirectML decode with native CPU.

Run with the application Python after export_radeon_codec.py. This starts its
own worker, writes WAV/JSON evidence, and does not restart a running engine.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

BOX = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=BOX / "work" / "radeon-decode-validation")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for key, value in {
        "IRODORI_CHECKPOINT": BOX / "models" / "model.safetensors",
        "IRODORI_RUNTIME_DIR": BOX / "runtime",
        "IRODORI_HF_HOME": BOX / ".cache" / "huggingface",
        "IRODORI_CACHE_DIR": args.out_dir / "cache",
    }.items():
        os.environ[key] = str(value)
    sys.path.insert(0, str(BOX / "irodori-tts" / "wrapper"))
    import torch
    from tts_cli import RadeonBackend, _import_runtime

    torch.set_num_threads(2)
    backend = RadeonBackend(project_root=BOX)
    _, _, _, SamplingRequest, save_wav = _import_runtime()
    codec = backend.runtime.codec
    cpu_decode = type(codec).decode_latent.__get__(codec, type(codec))
    captures = []

    def capture_decode(latent):
        audio = backend.bridge.decode(latent)
        captures.append((latent.detach().cpu().clone(), audio.clone()))
        return audio

    codec.decode_latent = capture_decode
    rows = []
    try:
        # Repeat one shape to measure the resident session after initialization.
        cases = [
            ("short", "こんにちは。今日はいい天気ですね。", 2.0),
            ("medium", "音声のデコードも、ラデオンのグラフィックスで処理できるようになりました。", 4.0),
            ("medium_warm", "音声のデコードも、ラデオンのグラフィックスで処理できるようになりました。", 4.0),
        ]
        for name, text, seconds in cases:
            captures.clear()
            request = SamplingRequest(text=text, no_ref=True, num_steps=8, seed=1001,
                                      seconds=seconds, decode_mode="batch",
                                      t_schedule_mode="sway", sway_coeff=-1.0)
            result = backend.synthesize(request, None, args.out_dir / f"{name}.wav")
            comparisons = []
            for index, (latent, gpu_audio) in enumerate(captures):
                start = time.perf_counter()
                cpu_audio = cpu_decode(latent)
                cpu_s = time.perf_counter() - start
                torch.testing.assert_close(gpu_audio, cpu_audio, rtol=1e-3, atol=2e-5)
                delta = gpu_audio - cpu_audio
                comparisons.append({"latent_shape": list(latent.shape),
                                    "audio_shape": list(gpu_audio.shape), "cpu_decode_s": cpu_s,
                                    "max_abs": delta.abs().max().item(),
                                    "rmse": delta.square().mean().sqrt().item()})
                save_wav(str(args.out_dir / f"{name}_cpu_{index}.wav"), cpu_audio[0], codec.sample_rate)
            row = {"case": name, "result": result, "comparisons": comparisons}
            rows.append(row)
            print(json.dumps(row, ensure_ascii=True), flush=True)
        # A batch >1 exercises the dynamic batch dimension and float conversion.
        latent = captures[0][0][:, :16].repeat(2, 1, 1)
        gpu_audio = backend.bridge.decode(latent.double())
        torch.testing.assert_close(gpu_audio, cpu_decode(latent), rtol=1e-3, atol=2e-5)
        report = {"codec": backend.codec_info, "rows": rows, "batch_two_shape": list(gpu_audio.shape)}
        (args.out_dir / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        backend.close()


if __name__ == "__main__":
    main()
