# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("ml_lab/ui/tabs/tab_curves_studio.py")
s = p.read_text(encoding="utf-8")

# SweepWorker: signature + attr
old = '''        param_values: list[Any],
        cv_folds: int = 5,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.algo = algo
        self.param_name = param_name
        self.param_values = param_values
        self.cv_folds = cv_folds'''
new = '''        param_values: list[Any],
        cv_folds: int = 5,
        include_standby: bool = False,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.algo = algo
        self.param_name = param_name
        self.param_values = param_values
        self.cv_folds = cv_folds
        self.include_standby = include_standby'''
assert old in s, "sweep anchor"
s = s.replace(old, new, 1)

# SweepWorker.run: split call (val_fraction=0.01)
old = '''                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.01,
                    window_size=64,
                    step_size=16,
                )'''
new = '''                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.01,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
                )'''
assert old in s, "sweep split anchor"
s = s.replace(old, new, 1)

# DataSizeWorker
old = '''    def __init__(self, dataset_dir: Path, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir

    FRACTIONS'''
new = '''    def __init__(self, dataset_dir: Path, include_standby: bool = False, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.include_standby = include_standby

    FRACTIONS'''
assert old in s, "datasize anchor"
s = s.replace(old, new, 1)

old = '''                train_samples, val_samples, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.2,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
                )'''
new = '''                train_samples, val_samples, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.2,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
                )'''
if old not in s:
    old2 = '''                train_samples, val_samples, class_names = split_user_dataset_file_level(
                    self.dataset_dir, val_fraction=0.2, window_size=64, step_size=16
                )'''
    new2 = '''                train_samples, val_samples, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.2,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
                )'''
    assert old2 in s, "datasize split anchor"
    s = s.replace(old2, new2, 1)

p.write_text(s, encoding="utf-8")
print("curves workers patched")
