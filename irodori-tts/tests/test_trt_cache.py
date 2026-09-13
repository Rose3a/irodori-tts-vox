import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'wrapper'))
import trt_cache


class CacheTests(unittest.TestCase):
    def test_identity_changes_invalidate_key(self):
        base = dict(model='a', gpu='RTX', trt='10', sources={'exporter': 'a'})
        for field in base:
            self.assertNotEqual(trt_cache.cache_key(base),
                                trt_cache.cache_key({**base, field: 'changed'}))
        self.assertEqual(trt_cache.cache_key(base),
                         trt_cache.cache_key(dict(reversed(list(base.items())))))

    def test_requires_verified_undamaged_matching_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            identity = dict(model='a')
            plan = folder / 'fallback_bf16.plan'
            plan.write_bytes(b'plan')
            self.assertFalse(trt_cache.valid_cache(folder, identity))
            (folder / 'ready.json').write_text(json.dumps(dict(
                identity=identity, plan_sha256=trt_cache.digest(plan))))
            self.assertTrue(trt_cache.valid_cache(folder, identity))
            self.assertFalse(trt_cache.valid_cache(folder, dict(model='b')))
            plan.write_bytes(b'corrupt')
            self.assertFalse(trt_cache.valid_cache(folder, identity))

    def test_failed_build_never_publishes_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            box = Path(temp)
            with patch.object(trt_cache, 'BOX', box), \
                 patch.object(trt_cache, 'cache_identity', return_value={'model': 'a'}), \
                 patch.object(trt_cache.subprocess, 'run') as run:
                run.return_value.returncode = 1
                with self.assertRaisesRegex(RuntimeError, 'CUDA'):
                    trt_cache.ensure_plan(box / 'model', lambda *a: None, lambda *a: None)
            self.assertEqual(list(box.rglob('ready.json')), [])

    def test_failure_reports_child_exception_and_uses_capture(self):
        with tempfile.TemporaryDirectory() as temp:
            box = Path(temp)
            def fail(args, **kwargs):
                self.assertEqual(args[-1], 'capture')
                self.assertEqual(kwargs['env']['PYTHONIOENCODING'], 'utf-8')
                kwargs['stdout'].write('Traceback:\nRuntimeError: 変換エラー\n')
                return type('Result', (), {'returncode': 1})()
            with patch.object(trt_cache, 'BOX', box), \
                 patch.object(trt_cache, 'cache_identity', return_value={'model': 'a'}), \
                 patch.object(trt_cache.subprocess, 'run', side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, 'RuntimeError: 変換エラー'):
                    trt_cache.ensure_plan(box / 'model', lambda *a: None, lambda *a: None)


if __name__ == '__main__':
    unittest.main()
