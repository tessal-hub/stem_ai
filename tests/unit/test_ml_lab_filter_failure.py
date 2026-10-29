from types import SimpleNamespace

from ml_lab.ui.window_ml_lab import MlLabWindow


def test_failed_spell_selection_fails_closed():
    class BrokenFilter:
        _counts = {"TEST_ALPHA": 3}

        def get_selected(self):
            raise OSError("dataset state unavailable")

    lab = SimpleNamespace(filter_bar=BrokenFilter())

    assert MlLabWindow._current_allowed_spells(lab) == set()
