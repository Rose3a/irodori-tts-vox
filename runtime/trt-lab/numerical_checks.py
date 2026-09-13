"""Quality gates for the BF16 export wrapper, independent of CUDA imports."""
import json
import torch


def validate_export(actual, expected):
    if actual.shape != expected.shape or actual.numel() == 0:
        raise RuntimeError('Export output shape mismatch or empty output')
    actual, expected = actual.float(), expected.float()
    if not torch.isfinite(actual).all() or not torch.isfinite(expected).all():
        raise RuntimeError('Export output contains NaN or infinity')
    error = (actual - expected).abs()
    original_limit = 0.05 + 0.05 * expected.abs()
    metrics = dict(
        elements=actual.numel(),
        outside_original_tolerance=int((error > original_limit).sum().item()),
        max_abs=error.max().item(),
        relative_rmse=(error.square().mean().sqrt()
                       / expected.square().mean().sqrt().clamp_min(1e-6)).item(),
    )
    # A near-zero reference can turn a small BF16 difference into a large
    # relative error. Permit sparse outliers only with a small overall error
    # AND a per-element ceiling. These are export screening thresholds, not
    # a claim that perceptual audio quality has been validated.
    if (metrics['outside_original_tolerance'] / metrics['elements'] > 0.001
            or metrics['relative_rmse'] > 0.01
            or bool((error > (0.10 + 0.05 * expected.abs())).any())):
        raise RuntimeError('BF16 export comparison failed: ' + json.dumps(metrics))
    return metrics
