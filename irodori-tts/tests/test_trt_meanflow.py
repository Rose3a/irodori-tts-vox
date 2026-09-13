"""Exercise the real adapter without importing CUDA/TensorRT on the test PC."""
import ast
from collections import OrderedDict
from pathlib import Path
import types
import unittest
import torch

BOX = Path(__file__).resolve().parents[2]


def load_class(file, name, scope):
    tree = ast.parse(file.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(file), 'exec'), scope)
    return scope[name]


class MeanFlowTests(unittest.TestCase):
    def test_adapter_updates_delta_each_step_while_reusing_kv(self):
        captured = []
        class Engine:
            input_names = ['x', 't', 'delta_t']
            def __call__(self, xs):
                captured.append(xs)
        prepare_calls = []
        def inputs(model, kw, compact):
            prepare_calls.append(1)
            return (kw['x_t'], kw['t'], *[torch.ones(1)] * 11, kw['delta_t'])
        adapter_class = load_class(BOX / 'runtime/trt-lab/run_engine.py', 'Adapter',
                                   dict(OrderedDict=OrderedDict, inputs_from=inputs))
        adapter = adapter_class(types.SimpleNamespace(delta_cond_module=True), Engine())
        kw = dict(x_t=torch.ones(1, 2), t=torch.ones(1), context_kv_cache=[1])
        adapter(**kw, delta_t=torch.tensor([0.25]))
        adapter(**kw, delta_t=torch.tensor([0.125]))
        self.assertEqual(len(prepare_calls), 1)
        self.assertEqual(captured[0][-1].item(), 0.25)
        self.assertEqual(captured[1][-1].item(), 0.125)
        self.assertEqual(len(captured[1]), 14)

    def test_export_wrapper_includes_meanflow_condition(self):
        wrapper_class = load_class(BOX / 'runtime/trt-lab/trt_experiment.py', 'CachedDiT',
            dict(torch=torch, model_module=types.SimpleNamespace(
                get_timestep_embedding=lambda t, dim: t[:, None])))
        for meanflow in (False, True):
            model = types.SimpleNamespace(in_proj=torch.nn.Identity(),
                cond_module=torch.nn.Identity(), blocks=torch.nn.ModuleList(),
                out_norm=torch.nn.Identity(), out_proj=torch.nn.Identity(),
                cfg=types.SimpleNamespace(timestep_embed_dim=1),
                delta_cond_module=torch.nn.Identity() if meanflow else None)
            class Block(torch.nn.Module):
                def forward(self, h, cond, *args, **kwargs):
                    return h + cond
            model.blocks.append(Block())
            wrapper = wrapper_class(model)
            kv = [torch.zeros(1, 1)] * 6
            if meanflow:
                kv.append(torch.tensor([0.25]))
            actual = wrapper(torch.zeros(1, 1, 1), torch.tensor([0.5]),
                             None, None, None, torch.ones(1), torch.zeros(1), *kv)
            self.assertEqual(actual.item(), 0.75 if meanflow else 0.5)


if __name__ == '__main__':
    unittest.main()
