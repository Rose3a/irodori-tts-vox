"""Download assets and verify the actual inference imports before marking setup ready."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

BOX = Path(__file__).resolve().parents[1]
os.environ['HF_HOME'] = str(BOX / '.cache' / 'huggingface')
sys.path.insert(0, str(BOX / 'runtime' / 'trt-lab' / 'repo'))

def verify_audio_io():
    """Exercise the runtime's WAV export, including its SoundFile fallback."""
    import torch
    from irodori_tts.inference_runtime import save_wav, _load_audio

    with tempfile.TemporaryDirectory(prefix='irodori-audio-check-') as folder:
        for channels in (1, 2):
            samples = torch.linspace(-0.25, 0.25, 3200).repeat(channels, 1)
            path = save_wav(Path(folder) / f'{channels}ch.wav', samples, 32000)
            restored, rate = _load_audio(path)
            if rate != 32000 or restored.shape != samples.shape:
                raise RuntimeError('WAV round-trip changed sample rate or channel layout.')
            if not torch.allclose(restored, samples, atol=1e-4, rtol=0):
                raise RuntimeError('WAV round-trip changed audio samples.')
    print('WAV export and read verified (mono/stereo).', flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', choices=['cuda', 'cpu', 'radeon'], required=True)
    args = parser.parse_args()
    import torch
    verify_audio_io()
    if args.backend == 'cuda':
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA is unavailable. Update the NVIDIA driver, then retry setup.')
        print('CUDA test:', torch.cuda.get_device_name(0), flush=True)
        print((torch.ones(4, device='cuda') * 2).cpu(), flush=True)
    from huggingface_hub import hf_hub_download
    from safetensors import safe_open
    from irodori_tts.inference_runtime import InferenceRuntime
    from irodori_tts.tokenizer import PretrainedTextTokenizer
    from dacvae import DACVAE
    checkpoint = BOX / 'models' / 'model.safetensors'
    if not checkpoint.is_file():
        hf_hub_download('Aratako/Irodori-TTS-v4.1-Small', 'model.safetensors', local_dir=str(checkpoint.parent))
    with safe_open(str(checkpoint), framework='pt') as f:
        metadata = f.metadata() or {}
        print('Checkpoint metadata:', list(metadata), flush=True)
    hf_hub_download('Aratako/Semantic-DACVAE-Japanese-32dim', 'weights.pth')
    config = json.loads(metadata['config_json'])
    for repo in {config['text_tokenizer_repo'], config.get('caption_tokenizer_repo') or config['text_tokenizer_repo']}:
        PretrainedTextTokenizer.from_pretrained(repo, revision=config.get('text_encoder_revision'))
    settings = BOX / 'irodori-tts' / 'editor-settings.json'
    value = dict(backend=args.backend, model='model.safetensors', steps=8, seed=1001, seconds=None)
    if settings.exists():
        try: value.update(json.loads(settings.read_text(encoding='utf-8-sig')))
        except (ValueError, OSError): pass
    value['backend'] = args.backend
    settings.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Runtime imports and model download verified.', flush=True)

if __name__ == '__main__':
    main()
