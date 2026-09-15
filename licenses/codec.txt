---
license: mit
language:
- ja
base_model:
- Aratako/Semantic-DACVAE-Japanese
pipeline_tag: audio-to-audio
tags:
- VAE
- Speech
- Voice
---

# Semantic-DACVAE-Japanese-32dim

**Semantic-DACVAE-Japanese-32dim** is a variant of our previous [Semantic-DACVAE-Japanese](https://huggingface.co/Aratako/Semantic-DACVAE-Japanese) model. While the core model architecture and parameter count remain the same, the latent dimension has been aggressively compressed from the original 128 to 32. This makes the latent representations much more compact while still maintaining high-quality Japanese speech reconstruction.

Like its predecessor, this model is based on [facebook/dacvae-watermarked](https://huggingface.co/facebook/dacvae-watermarked) and integrates WavLM semantic distillation inspired by the [Semantic-VAE paper](https://arxiv.org/abs/2509.22167). It has been fine-tuned extensively on Japanese speech datasets to achieve more natural reconstructions.

According to the Semantic-VAE paper, this semantic distillation approach improves the training efficiency and performance of downstream TTS models. Furthermore, by reducing the latent dimension to 32, this new variant enables even lighter and faster training for these downstream tasks without sacrificing much audio quality.

## 🌟 Overview

* **Base Model:** Derived from [Semantic-DACVAE-Japanese](https://huggingface.co/Aratako/Semantic-DACVAE-Japanese) (originally [facebook/dacvae-watermarked](https://huggingface.co/facebook/dacvae-watermarked)).
* **Enhancements:**
  * Integrated WavLM semantic distillation.
  * Latent dimension reduced to 32 (down from 128).
* **Training Data:** Fine-tuned explicitly on Japanese speech datasets.
* **License:** MIT

## 📊 Evaluation

We evaluated the model using the **UTMOSv2** metric to measure the quality of the reconstructed audio. Despite the aggressive reduction in latent dimensions (128 → 32), this model maintains a highly competitive naturalness score, outperforming the original base model.

### 1. Emilia-YODAS (Japanese Subset)
Tested on 100 samples (not included in training) from the Japanese subset of [amphion/Emilia-Dataset](https://huggingface.co/datasets/amphion/Emilia-Dataset).

| Audio Source | Mean UTMOSv2 (n=100) |
| :--- | :---: |
| **Original Audio** | 2.2099 |
| **facebook/dacvae-watermarked** | 2.2841 |
| **Aratako/Semantic-DACVAE-Japanese** (128-dim) | 2.4812 |
| **Aratako/Semantic-DACVAE-Japanese-32dim** | **2.4024** |

### 2. Private Test Dataset (Japanese)
Tested on 100 private Japanese speech samples.

| Audio Source | Mean UTMOSv2 (n=100) |
| :--- | :---: |
| **Original Audio** | 2.0322 |
| **facebook/dacvae-watermarked** | 1.8775 |
| **Aratako/Semantic-DACVAE-Japanese** (128-dim) | 2.1629 |
| **Aratako/Semantic-DACVAE-Japanese-32dim** | **2.1421** |

## 🚀 Quick Start

### Installation

First, set up your environment and install the official repository:

```bash
# Create a virtual environment
uv venv --python=3.10

# Install the official dacvae package
uv pip install https://github.com/facebookresearch/dacvae

```

### Inference

Below is a basic example of inference.

```python
import soundfile as sf
import torch
import torchaudio
from audiotools import AudioSignal
from dacvae import DACVAE
from huggingface_hub import hf_hub_download

# 1. Load the model
model = DACVAE.load(hf_hub_download(repo_id="Aratako/Semantic-DACVAE-Japanese-32dim", filename="weights.pth")).eval()

# Disable/bypass the default watermark since this model was fine-tuned without it
model.decoder.alpha = 0.0
model.decoder.watermark = lambda x, message=None, d=model.decoder: d.wm_model.encoder_block.forward_no_conv(x)

# 2. Load and preprocess audio
wav_np, sr = sf.read("input.wav", dtype="float32")
wav = torch.from_numpy(wav_np.T) if wav_np.ndim == 2 else torch.from_numpy(wav_np).unsqueeze(0)
wav = torchaudio.functional.resample(wav.mean(0, keepdim=True), sr, model.sample_rate)

signal = AudioSignal(wav.unsqueeze(0), model.sample_rate)
signal.normalize(-16.0)
signal.ensure_max_of_audio()
x = signal.audio_data.float()  # (1, 1, T)

# 3. Encode and Decode
with torch.no_grad():
    z = model.encoder(model._pad(x))
    z, _ = model.quantizer.in_proj(z).chunk(2, dim=1)
    y = model.decode(z)[0].cpu()

# 4. Save reconstructed audio
sf.write("recon.wav", y.squeeze(0).numpy(), model.sample_rate)

```

## 📜 Acknowledgements

* **Base Model:** Weights derived from [facebook/dacvae-watermarked](https://huggingface.co/facebook/dacvae-watermarked).
* **Training Code:** Leveraged the codebase from [Descript Audio Codec (DAC)](https://github.com/descriptinc/descript-audio-codec).
* **Methodology:** Semantic distillation approach heavily inspired by the [Semantic-VAE paper](https://arxiv.org/abs/2509.22167).

## 🖊️ Citation

```bibtex
@misc{semantic-dacvae-japanese-32dim,
  author = {Chihiro Arata},
  title = {Semantic-DACVAE-Japanese-32dim: Lightweight Audio VAE for Japanese Speech},
  year = {2026},
  publisher = {Hugging Face},
  journal = {Hugging Face repository},
  howpublished = {\url{https://huggingface.co/Aratako/Semantic-DACVAE-Japanese-32dim}}
}
```