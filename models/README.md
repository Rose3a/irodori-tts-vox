---
license: mit
language:
- ja
pipeline_tag: text-to-speech
tags:
- speech
- voice
- tts
base_model:
- Aratako/Irodori-TTS-v4-Small
---

# Irodori-TTS-v4.1-Small

[![Code](https://img.shields.io/badge/Code-GitHub-black)](https://github.com/Aratako/Irodori-TTS) [![Demo Space](https://img.shields.io/badge/Demo-HuggingFace%20Space-blue)](https://huggingface.co/spaces/Aratako/Irodori-TTS-v4.1-Small-Demo)

This checkpoint is a minor update to [Irodori-TTS-v4-Small](https://huggingface.co/Aratako/Irodori-TTS-v4-Small) with an improved duration predictor.

Only the duration predictor was replaced and retrained. The RF-DiT, text and caption encoder, speaker encoder, and conditioning modules are unchanged from the base model. Voice cloning, Voice Design, long-reference conditioning, and emoji-based style control therefore remain available with the same inference interface.

## ✨ Update

The original checkpoint trained the main model and duration predictor together. In this checkpoint, the duration predictor was trained separately after the main model had converged, while all other model parameters remained frozen. This improves automatic duration estimation and reduces generation errors caused by overestimated output lengths. No code changes are required to use this checkpoint.

## 🚀 Usage

For inference code, installation instructions, and training scripts, please refer to the GitHub repository:

👉 **[GitHub: Aratako/Irodori-TTS](https://github.com/Aratako/Irodori-TTS)**

For lower-memory inference, torchao INT8, INT4, and FP8 variants are available at **[Aratako/Irodori-TTS-v4.1-Small-Quantized](https://huggingface.co/Aratako/Irodori-TTS-v4.1-Small-Quantized)**.

## 📊 Benchmarks

The updated and original checkpoints were evaluated under matched settings: FP32 inference, 40 RF steps, text CFG 3.0, no reference audio or caption. Values are the mean and population standard deviation across the consecutive base sampling seeds 0 through 4.

Neither the [Joyo Kanji Yomi Benchmark](https://github.com/sbintuitions/Joyo-Kanji-Yomi-Benchmark) nor JSUT was included in the training data.

### Japanese Reading

#### Joyo Kanji Yomi Benchmark

| Model | Kana-CER ↓ | Kana-CER clipped ↓ | Sentence Kana-CER ↓ | Standard CER ↓ |
| :--- | ---: | ---: | ---: | ---: |
| Irodori-TTS-600M-v3-VoiceDesign | 8.49 ± 0.21% | 5.59 ± 0.09% | 2.45 ± 0.02% | 4.88 ± 0.21% |
| Irodori-TTS-v4-Small (original) | 7.43 ± 0.17% | 5.08 ± 0.03% | 2.89 ± 0.03% | 5.35 ± 0.18% |
| **Irodori-TTS-v4.1-Small** | **7.29 ± 0.13%** | **5.03 ± 0.03%** | **2.36 ± 0.01%** | **4.69 ± 0.02%** |

#### JSUT BASIC5000

| Model | Sentence Kana-CER ↓ | Standard CER ↓ |
| :--- | ---: | ---: |
| Irodori-TTS-600M-v3-VoiceDesign | 3.62 ± 0.03% | **7.19 ± 0.05%** |
| Irodori-TTS-v4-Small (original) | 3.49 ± 0.02% | 7.32 ± 0.09% |
| **Irodori-TTS-v4.1-Small** | **3.43 ± 0.01%** | 7.22 ± 0.12% |

## ⚠️ Limitations

  - **Japanese Only:** This model currently supports Japanese text input only.
  - **Short-reference Voice Cloning:** With only one short reference clip, objective speaker similarity was modestly lower than v3 in the evaluation. Approximately 30 seconds or more of reasonably clean reference speech is recommended when available.
  - **Long-reference Composition:** Training and long-reference evaluation used multiple short utterances from the same speaker concatenated together. A single uninterrupted long recording is supported as input, but its effect has not been evaluated.
  - **Conditioning Conflicts:** When using both reference audio and a text caption, contradictory instructions may result in unstable audio quality, unnatural artifacts, or one condition overriding the other. For optimal results, use the caption to guide emotion, style, or environment while keeping the base voice characteristics aligned with the reference audio.
  - **Prompt Adherence:** While the model generally follows caption instructions, highly complex or contradictory descriptions may produce inconsistent results.
  - **Emoji Control:** The effect of emoji-based control may vary depending on context and is not always perfectly consistent.
  - **Kanji Reading:** Difficult Kanji reading has improved over v3, but uncommon names, specialized terminology, and context-dependent readings may still be pronounced incorrectly.
  - **Evaluation Scope:** No large-scale human MOS, naturalness, prompt-adherence, or speaker-similarity evaluation was conducted. Automatic benchmark scores do not fully represent human perception.

## 📜 License & Ethical Restrictions

### License

This model is released under **[MIT](https://choosealicense.com/licenses/mit/)**.

### Ethical Restrictions

In addition to the license terms, the following ethical restrictions apply:

1.  **No Impersonation:** Do not use this model to clone or impersonate the voice of any individual (e.g., voice actors, celebrities, public figures) without their explicit consent.
2.  **No Misinformation:** Do not use this model to generate deepfakes or synthetic speech intended to mislead others or spread misinformation.
3.  **Voice Generation Disclaimer:** When generating speech purely from text or captions without using reference audio, it is possible that the generated voice may coincidentally resemble that of a real person. This is strictly a probabilistic artifact within the latent space. The model was not trained with the intent of reproducing specific individuals.
4.  **Liability Disclaimer:** The developers assume no liability for any misuse of this model. Users are solely responsible for ensuring their use of the generated content complies with applicable laws and regulations in their jurisdiction.

## 🙏 Acknowledgments

This project builds upon the following works:

  - [Echo-TTS](https://jordandarefsky.com/blog/2025/echo/) — Architecture and training design reference
  - [DACVAE](https://github.com/facebookresearch/dacvae) — Audio VAE
  - [sbintuitions/modernbert-ja-310m](https://huggingface.co/sbintuitions/modernbert-ja-310m) — Pretrained Japanese text and caption encoder
  - [SilentCipher](https://github.com/sony/silentcipher) — Audio watermarking integration

We would also like to extend our special thanks to **[Respair](https://huggingface.co/Respair)** for the inspiration behind the emoji annotation feature, and to [gabrielclark3330](https://huggingface.co/gabrielclark3330) and [kikouousya](https://huggingface.co/kikouousya) for supporting this project.

## 🖊️ Citation

If you use Irodori-TTS in your research or project, please cite it as follows:

```bibtex
@misc{irodori-tts-v4.1-small,
  author = {Chihiro Arata},
  title = {Irodori-TTS: A Flow Matching-based Text-to-Speech Model with Emoji-driven Style Control},
  year = {2026},
  publisher = {Hugging Face},
  journal = {Hugging Face repository},
  howpublished = {\url{https://huggingface.co/Aratako/Irodori-TTS-v4.1-Small}}
}
```
