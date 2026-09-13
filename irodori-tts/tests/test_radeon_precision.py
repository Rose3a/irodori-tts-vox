import ast
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "irodori-tts" / "wrapper"
sys.path.insert(0, str(WRAPPER))

_cli_tree = ast.parse((WRAPPER / "tts_cli.py").read_text(encoding="utf-8"))
_precision_node = next(node for node in _cli_tree.body
                       if isinstance(node, ast.FunctionDef)
                       and node.name == "parse_radeon_precision")
_precision_module = ast.Module(body=[_precision_node], type_ignores=[])
_precision_ns = {"os": os}
exec(compile(_precision_module, "tts_cli.py", "exec"), _precision_ns)
parse_radeon_precision = _precision_ns["parse_radeon_precision"]


class RadeonPrecisionTests(unittest.TestCase):
    def test_precision_defaults_to_fp32_and_accepts_fp16(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(parse_radeon_precision(), "fp32")
        self.assertEqual(parse_radeon_precision("FP16"), "fp16")

    def test_invalid_precision_is_actionable(self):
        with self.assertRaisesRegex(ValueError, "expected fp32 or fp16"):
            parse_radeon_precision("bf16")

    def test_worker_command_propagates_precision(self):
        source = (WRAPPER / "radeon_bridge.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertIn('"--precision", precision', source)
        self.assertTrue(any(isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "Popen"
                            for node in ast.walk(tree)))

    def test_fp16_worker_keeps_masks_bool_and_returns_fp32(self):
        source = (WRAPPER / "radeon_worker.py").read_text(encoding="utf-8")
        self.assertIn("core = core.half()", source)
        self.assertIn("dtype=torch.bool", source)
        self.assertIn("output = core(x, t", source)
        self.assertIn(".float().cpu()", source)

    def test_codec_contract_is_precision_aware(self):
        source = (WRAPPER / "radeon_codec.py").read_text(encoding="utf-8")
        self.assertIn("irodori_codec_precision", source)
        self.assertIn("tensor(float16)", source)
        self.assertIn("np.float16", source)
        self.assertIn("return np.asarray(audio, dtype=np.float32)", source)

    def test_exporter_has_separate_precision_contract(self):
        source = (ROOT / "tools" / "export_radeon_codec.py").read_text(encoding="utf-8")
        self.assertIn('--precision', source)
        self.assertIn('irodori_codec_precision', source)
        self.assertIn('codec_decoder_fp16.onnx',
                      (WRAPPER / "tts_cli.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
