"""Variable-length Irodori waveform decoder running in the DirectML worker."""
from pathlib import Path

import numpy as np
import onnxruntime as ort


class DirectMLCodec:
    def __init__(self, path: str | Path, device_id: int, precision: str = "fp32"):
        if precision not in {"fp32", "fp16"}:
            raise ValueError(f"Unsupported Radeon codec precision: {precision}")
        self.precision = precision
        if "DmlExecutionProvider" not in ort.get_available_providers():
            raise RuntimeError("Radeon audio decode requires onnxruntime-directml in the worker environment")
        options = ort.SessionOptions()
        options.enable_mem_pattern = False
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.intra_op_num_threads = 2
        # Fail visibly if a graph cannot run on this GPU, instead of reporting
        # a CPU decode as DirectML. Shape calculations may still run on host.
        options.add_session_config_entry("session.disable_cpu_ep_fallback", "1")
        try:
            self.session = ort.InferenceSession(
                str(path), sess_options=options,
                providers=[("DmlExecutionProvider", {"device_id": device_id})],
            )
        except Exception as exc:
            raise RuntimeError(
                "Cannot initialize Radeon audio decode on DirectML. For an old codec, "
                "regenerate it with tools/export_radeon_codec.py using the application Python. "
                f"ONNX Runtime error: {exc!r}"
            ) from exc
        metadata = self.session.get_modelmeta().custom_metadata_map
        if metadata.get("irodori_codec_version") != "2":
            raise RuntimeError(
                "Outdated Radeon ONNX codec. Regenerate it with tools/export_radeon_codec.py "
                "using the application Python; the decoder must use the Irodori mono output path."
            )
        self.hop_length = int(metadata["irodori_codec_hop_length"])
        self.sample_rate = int(metadata["irodori_codec_sample_rate"])
        metadata_precision = metadata.get("irodori_codec_precision", "fp32")
        if metadata_precision != precision:
            raise ValueError(
                f"Radeon codec precision mismatch: requested {precision}, "
                f"metadata says {metadata_precision!r}")
        inputs = self.session.get_inputs()
        outputs = self.session.get_outputs()
        if (len(inputs) != 1 or inputs[0].name != "latent"
                or inputs[0].type != ("tensor(float16)" if precision == "fp16" else "tensor(float)" )
                or len(inputs[0].shape) != 3
                or inputs[0].shape[2] != 32 or isinstance(inputs[0].shape[1], int)
                or len(outputs) != 1 or outputs[0].name != "audio"
                or outputs[0].type != ("tensor(float16)" if precision == "fp16" else "tensor(float)")
                or self.hop_length <= 0 or self.sample_rate <= 0):
            raise ValueError("Invalid Radeon codec contract: expected variable [batch, frames, 32] -> mono audio")

    def decode(self, latent: np.ndarray) -> np.ndarray:
        if latent.ndim != 3 or latent.shape[2] != 32 or min(latent.shape[:2]) <= 0:
            raise ValueError(f"Expected nonempty latent [batch, frames, 32], got {latent.shape}")
        latent = np.ascontiguousarray(latent, dtype=np.float16 if self.precision == "fp16" else np.float32)
        if not np.isfinite(latent).all():
            raise ValueError("Non-finite Radeon codec input")
        audio = self.session.run(["audio"], {"latent": latent})[0]
        expected = (latent.shape[0], 1, latent.shape[1] * self.hop_length)
        if audio.shape != expected or not np.isfinite(audio).all():
            raise RuntimeError(f"Invalid Radeon codec output: shape={audio.shape}, expected={expected}")
        return np.asarray(audio, dtype=np.float32)
