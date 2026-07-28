"""Verify fallback validation split does not randomly shuffle overlapping windows."""
import inspect

def test_fallback_val_split_uses_temporal_order():
    from logic.tensorflow.pipeline import build_gesture_model
    source = inspect.getsource(build_gesture_model)
    # Check fallback split block does NOT use perm_base permutation
    assert "perm_base = np.random" not in source, \
        "Fallback val split still randomly shuffles overlapping base windows (data leakage)"
