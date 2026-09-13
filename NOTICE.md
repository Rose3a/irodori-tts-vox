# Third-party notices and distribution boundaries

This repository combines original integration code with modified upstream projects. Files retain the license that applies to their source; this notice does not replace any upstream license text.

## Source code

| Path | Upstream / copyright | License | Required action when redistributing |
| --- | --- | --- | --- |
| `runtime/trt-lab/repo/` | Aratako / Irodori-TTS (modified subset, see below) | MIT | Keep `runtime/trt-lab/repo/LICENSE` and its copyright notice. |
| `voicevox-editor/` | VOICEVOX contributors (modified, see below) | LGPL-3.0 or separately obtained license | Keep `voicevox-editor/LICENSE` and `voicevox-editor/LGPL_LICENSE`; provide the corresponding source and preserve notices for modified Editor code. |
| `voicevox-editor/public/licenses.json` | JavaScript dependencies | Per-package licenses | Regenerate when Editor dependencies change. |
| `speakers/thumbnails/default-speaker.png` | Original generated fallback asset | Project-owned asset | Used only when a speaker has no portrait image. |

## Modifications to upstream code

Both upstream copies in this repository are modified, not pristine checkouts.

- `runtime/trt-lab/repo/` keeps 25 of the 55 files published by Irodori-TTS and
  changes the inference path for this project's CLI, TensorRT and DirectML
  backends, including `irodori_tts/inference_runtime.py`, `meanflow.py`,
  `codec.py` and `attention.py`. Modified 2026-09-06 through 2026-09-14.
- `voicevox-editor/` is a modified VOICEVOX Editor: the Irodori engine settings,
  the extra project/query fields, portrait, lip-sync and dictionary handling,
  the engine bootstrap and the Irodori help pages were added or changed.
  Modified 2026-09-06 through 2026-09-14. Upstream `LICENSE` and
  `LGPL_LICENSE` files are kept unchanged.

Neither upstream project endorses this distribution. Version numbers and update
notifications of this repository belong to this project, not to upstream.

The integration code in this repository is distributed under the same LGPL-3.0 terms as the included modified `voicevox-editor` work unless a file states otherwise. The complete LGPL-3.0 text is available at `voicevox-editor/LGPL_LICENSE`.

## Excluded artifacts

The following are intentionally ignored and must not be added to a public source release without a separate rights review:

- Irodori model weights, tokenizer assets, TensorRT plans, and model caches.
- Speaker embeddings, portrait images, and imported-speaker logs.
- Generated audio, logs, profiling results, diagnostics, local settings, environments, and backup files.
- Downloaded or locally built executables, including Python tooling and Editor/engine binaries.

Model weights and codec assets are separate from source code. Obtain them only from their official distribution pages and follow the linked model-card terms. A speaker embedding or reference audio may implicate voice, portrait, publicity, copyright, and consent rights even when its file format is technically portable.

## Upstream references

- Irodori-TTS: <https://github.com/Aratako/Irodori-TTS>
- VOICEVOX Editor: <https://github.com/VOICEVOX/voicevox>
- VOICEVOX Engine: <https://github.com/VOICEVOX/voicevox_engine>

Before publishing a binary release, regenerate the Editor dependency notices and perform a separate review of all bundled binaries, model files, voice data, fonts, and images.
