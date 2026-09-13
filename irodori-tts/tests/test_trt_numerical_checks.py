from pathlib import Path
import sys
import unittest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'runtime/trt-lab'))
from numerical_checks import validate_export


class ExportComparisonTests(unittest.TestCase):
    def test_sparse_near_zero_outlier_from_report(self):
        reference = torch.ones(1, 248, 32)
        reference[0, 136, 25] = 0.0703125 / 4.1875
        actual = reference.clone()
        actual[0, 136, 25] += 0.0703125
        with self.assertRaises(AssertionError):
            torch.testing.assert_close(actual, reference, rtol=0.05, atol=0.05)
        metrics = validate_export(actual, reference)
        self.assertEqual(metrics['outside_original_tolerance'], 1)

    def test_large_sparse_error_is_rejected(self):
        reference = torch.ones(7936)
        actual = reference.clone()
        actual[0] += 1
        with self.assertRaises(RuntimeError):
            validate_export(actual, reference)

    def test_global_drift_is_rejected_even_within_old_pointwise_tolerance(self):
        with self.assertRaises(RuntimeError):
            validate_export(torch.ones(7936) * 1.03, torch.ones(7936))

    def test_frequent_outliers_are_rejected(self):
        reference = torch.ones(7936)
        reference[:16] = 0
        actual = reference.clone()
        actual[:16] += 0.07
        with self.assertRaises(RuntimeError):
            validate_export(actual, reference)

    def test_nonfinite_and_wrong_shape_are_rejected(self):
        for actual in (torch.tensor([float('nan')]), torch.tensor([float('inf')]), torch.ones(2)):
            with self.assertRaises(RuntimeError):
                validate_export(actual, torch.ones(1))

    def test_zero_reference_and_exact_match(self):
        self.assertEqual(validate_export(torch.zeros(5), torch.zeros(5))['relative_rmse'], 0)
        with self.assertRaises(RuntimeError):
            validate_export(torch.ones(5) * 0.001, torch.zeros(5))


if __name__ == '__main__':
    unittest.main()
