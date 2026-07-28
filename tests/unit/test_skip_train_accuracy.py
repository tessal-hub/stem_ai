"""Verify skip-train path does not report fake perfect accuracy."""
import inspect

def test_skip_train_does_not_fake_accuracy():
    from logic.tensorflow.pipeline import build_gesture_model
    source = inspect.getsource(build_gesture_model)
    assert 'DummyHistory' not in source, "Skip-train path still uses DummyHistory with 1.0 accuracy"
