"""MeanFlow must reuse duration-predictor conditions without extra encoding."""
from pathlib import Path
import sys
import types
import unittest

import torch


ROOT = Path(__file__).resolve().parents[2] / "runtime" / "trt-lab" / "repo"
sys.path.insert(0, str(ROOT))
from irodori_tts.meanflow import EncodedConditions, sample_euler_meanflow


class MeanFlowConditionReuseTests(unittest.TestCase):
    def test_supplied_conditions_skip_encoding_and_keep_one_forward_per_step(self):
        class FakeModel:
            device = torch.device("cpu")
            dtype = torch.float32
            cfg = types.SimpleNamespace(
                flow_parameterization="meanflow", patched_latent_dim=2
            )

            def __init__(self):
                self.encode_calls = 0
                self.forward_calls = 0

            def encode_conditions(self, **_kwargs):
                self.encode_calls += 1
                return conditions

            def build_context_kv_cache(self, **_kwargs):
                return "cache"

            def forward_with_encoded_conditions(self, *, x_t, **_kwargs):
                self.forward_calls += 1
                return torch.zeros_like(x_t)

        conditions = (
            torch.zeros(1, 1, 2), torch.ones(1, 1, dtype=torch.bool),
            None, None, None, None,
        )
        model = FakeModel()
        output = sample_euler_meanflow(
            model=model,
            text_input_ids=torch.zeros(1, 1, dtype=torch.long),
            text_mask=conditions[1],
            ref_latent=None,
            ref_mask=None,
            sequence_length=3,
            num_steps=4,
            seed=1,
            encoded_conditions=EncodedConditions(*conditions),
        )
        self.assertEqual(tuple(output.shape), (1, 3, 2))
        self.assertEqual(model.encode_calls, 0)
        self.assertEqual(model.forward_calls, 4)


if __name__ == "__main__":
    unittest.main()
