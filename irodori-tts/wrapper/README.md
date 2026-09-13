# Irodori bf16 TensorRT wrapper

Resident single-process wrapper around the `fallback_bf16.plan` TensorRT
engine plus a speaker-cassette layer. Re-uses the GPU plan and only
re-loads the chosen `.speaker.safetensors` from disk. Falls back to
PyTorch when CUDA is unavailable or the plan is missing.

## Files

- `wrapper/tts_cli.py` — Python wrapper, CLI, and HTTP server.
- `wrapper/run.bat` — one-shot synthesis from the command line.
- `wrapper/serve.bat` — starts a localhost HTTP server.

## Quick start

### Other Windows PCs

From the project root, double-click `setup_venv.bat`, or run:

```bat
setup_venv.bat
```

This creates a local `.venv` and installs the common PyTorch backend
dependencies. It checks the installed NVIDIA GPU with `nvidia-smi` and
automatically installs TensorRT when an RTX GPU is detected. On non-RTX or
CPU-only machines, TensorRT is skipped. The setup log is saved as
`setup_venv.log`, and the window waits for a key press when finished.

The setup also downloads `Aratako/Irodori-TTS-v4.1-Small` into `models`.
On RTX machines it then exports the bundled model runtime and builds
`bf16-fallback\fallback_bf16.plan` locally for that GPU and TensorRT version.
The setup installs the official DACVAE codec dependency as well; it is needed
before the first model load.

Then run the wrapper without editing any drive letters:

```bat
wrapper\run.bat --list-speakers
wrapper\run.bat --speaker fairy --text "hello" --out outputs\hello.wav
wrapper\serve.bat
```

引数なしの `run.bat` は対話モードで起動する。`interactive.bat` を直接
起動しても同じで、矢印キーで `torch` / `trt` / `cpu`、話者または
`話者なし` を選び、入力した文章を `outputs` に保存する。

The batch files use the project-local `.venv` first and resolve bundled
folders such as `embeddings`, `models`, `runtime`, and
`bf16-fallback\fallback_bf16.plan` relative to the project. If those assets
are stored elsewhere, set the corresponding `IRODORI_*` environment variable
before launching the batch file. `setup_venv.bat` downloads the base checkpoint,
bundles the runtime source used by this wrapper, and builds the TensorRT plan
on RTX machines. Speaker-inversion embeddings are still optional external
files; choose `(話者なし)` in interactive mode when none are available.

The cleanest way to run the wrapper is via Python directly, not via
`run.bat`. Use the bat only when you need a double-clickable entry point
on Windows; for command-line work call the script with the lab venv's
interpreter.

List the speakers (uses defaults unless `--embed-dir` is added):

```bat
E:\tts\trt-lab-20260905\.venv\Scripts\python.exe E:\tts\trt-slope-20260906\wrapper\tts_cli.py --list-speakers
```

Synthesise one utterance with an extra search root:

```bat
E:\tts\trt-lab-20260905\.venv\Scripts\python.exe E:\tts\trt-slope-20260906\wrapper\tts_cli.py ^
    --embed-dir .\embeddings ^
    --speaker local_fairy ^
    --text "hello cassette" ^
    --out outputs\out.wav ^
    --seed 1001
```

`run.bat` is provided for double-click launches. Because some older
versions of `cmd.exe` mishandle the embedded `rem` blocks and quoting,
it is best to keep the text short and avoid embedded spaces when
calling the bat from another program. From a fresh cmd prompt:

```bat
cd E:\tts\trt-slope-20260906\wrapper
run.bat --list-speakers
run.bat --speaker local_fairy --text "hello" --out outputs\out.wav --embed-dir .\embeddings
```

When the calling shell tokenises arguments (e.g. Python
`subprocess.run`), pass the bat through `cmd /c call` and quote
arguments carefully:

```python
import subprocess
subprocess.run(["cmd", "/c", "call", r"E:\tts\trt-slope-20260906\wrapper\run.bat",
                "--list-speakers", "--embed-dir", r".\embeddings"],
               capture_output=True, text=True, shell=False)
```

## Search-root configuration

`SpeakerCassette` looks for `*.speaker.safetensors` in this order, with
duplicates collapsed by canonical path:

1. Paths passed via `--embed-dir DIR` (repeatable; relative paths
   resolve against the current working directory).
2. Paths in the `IRODORI_EMBED_DIRS` environment variable (`;` or `,`
   separated).
3. Paths in the `IRODORI_EMBED_DIR` environment variable (single path).
4. The built-in defaults: `E:\tts\embeddings` and `D:\tts\embeddings`.

`--list-search-dirs` prints the resolved roots. The runtime cassette
re-scans on every call to `--list-speakers` / `--refresh-cassette`,
so dropping new embeddings into a registered directory is enough.

## HTTP server

```bat
serve.bat
serve.bat --port 9000
```

The server listens on `127.0.0.1`. From another machine use an SSH tunnel
(`ssh -L 9000:127.0.0.1:9000 user@host`).

Endpoints:

- `GET /speakers` — list of available speaker names plus default + backend
- `POST /synthesize` — JSON body:
  ```json
  {
    "text": "こんにちは",
    "speaker": "unleashguang",
    "out_wav": "optional\\path.wav",
    "seed": 1001,
    "num_steps": 8,
    "seconds": null
  }
  ```

## Speaker cassette

- Default search roots are `E:\tts\embeddings\` and `D:\tts\embeddings\`.
- Add any number of additional roots with `--embed-dir DIR` on the CLI
  or via `IRODORI_EMBED_DIRS=root1;root2`. Relative paths resolve
  against the current working directory.
- Each embedding is loaded from disk on first use and cached on the
  GPU (bf16, 1..64 × 768). Switching speakers reuses the resident
  TensorRT plan and rewrites a single small `.speaker.safetensors`
  cache file in `E:\tts\irodori-tts-cache\`.
- Both `fairy` and `fairy.speaker` are accepted as speaker names.
- Missing speaker raises a clear `FileNotFoundError` with the list of
  available names and the directories that were searched.
- `--refresh-cassette` re-scans the search paths and drops the GPU
  cache (also exposed at `GET /refresh` on the HTTP server).

## Backend selection

Resolution order:

1. `IRODORI_BACKEND=trt|torch` environment variable
2. `--backend trt|torch|auto` CLI flag (default `auto`)
3. `auto` picks `trt` if CUDA is available and
   `E:\tts\trt-slope-20260906\bf16-fallback\fallback_bf16.plan` exists,
   otherwise `torch`.

`torch` runs the same Irodori model on CPU (or CUDA without a plan).
Useful for verifying that a transcript-driven divergence is not
TensorRT-specific.

## Environment variables

| Name | Default | Notes |
|---|---|---|
| `IRODORI_BACKEND` | `auto` | `trt`, `torch`, or `auto` |
| `IRODORI_EMBED_DIR` | unset | single additional search root |
| `IRODORI_EMBED_DIRS` | unset | `;` or `,` separated additional search roots |
| `IRODORI_PLAN` | `E:\tts\trt-slope-20260906\bf16-fallback\fallback_bf16.plan` | trt backend only |
| `IRODORI_RUNTIME_DIR` | `E:\tts` | parent of `Irodori-TTS-Aratako` and `trt-lab-20260905` |
| `IRODORI_PYTHON` | `E:\tts\trt-lab-20260905\.venv\Scripts\python.exe` | venv interpreter |
| `IRODORI_CHECKPOINT` | `E:\tts\quantized\v41small.bf16.safetensors` | torch backend, also used by the trt runtime |
| `IRODORI_HF_HOME` | `E:\cache\huggingface` | HuggingFace cache for codec + text encoder |
| `IRODORI_CACHE_DIR` | `E:\tts\irodori-tts-cache` | where the active speaker is staged for the Irodori runtime |
| `IRODORI_RADEON_PRECISION` | `fp32` | Radeon only: `fp32` or opt-in `fp16`; invalid values fail clearly |
| `IRODORI_RADEON_CODEC_FP16` | `work\codec_decoder_fp16.onnx` | validated FP16 codec required when Radeon precision is `fp16` |

All paths can be overridden; nothing in the wrapper edits protected
files in `E:\tts\Irodori-TTS-Aratako` or any pre-existing plan.

FP16 Radeon launch (after exporting a compatible codec):
`$env:IRODORI_BACKEND='radeon'; $env:IRODORI_RADEON_PRECISION='fp16'; python wrapper\tts_cli.py --backend radeon --text 'テスト'`
Export candidate: `python tools\export_radeon_codec.py --precision fp16 --output work\codec_decoder_fp16.onnx`.
If FP16 export or validation fails, keep using the default FP32 codec/path; FP16 never silently reuses it.

## Verified

- `tts_cli.py --list-speakers` lists 38 speakers from
  `E:\tts\embeddings\` plus any others found in `--embed-dir`
  candidates.
- `tts_cli.py --speaker fairy --text "..."` produces a finite WAV.
- `serve.bat` accepts GET/POST. A 5-call `fairy → ug → fairy → ug → norma_ug`
  sequence runs the resident engine with no plan reloads
  (~0.18-0.33s per call).
- `--embed-dir .\embeddings` (relative to cwd) is resolved to an
  absolute path and prepended to the search list, so a project's
  own `.speaker.safetensors` are picked up alongside the shared
  `E:\tts\embeddings` defaults.
- `--list-search-dirs` prints the resolved roots in the order the
  cassette scans them.
