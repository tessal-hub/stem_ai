# -*- coding: utf-8 -*-
from pathlib import Path

def apply(path, pairs):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    missed = []
    for old, new in pairs:
        if new in s:
            continue
        if old in s:
            s = s.replace(old, new)
        else:
            missed.append(old[:70])
    p.write_text(s, encoding="utf-8")
    print(f"{path}: {len(missed)} missed")
    for m in missed:
        print("   MISS:", m)
    return missed

missed = []

# ── dataset_split ─────────────────────────────────────────────────────
missed += apply("ml_lab/data/dataset_split.py", [
    ('''def split_user_dataset_file_level(
    dataset_root: Path | str,
    val_fraction: float = 0.2,
    window_size: int = 64,
    step_size: int = 16,
    seed: int = 42,
) -> tuple[''',
     '''def split_user_dataset_file_level(
    dataset_root: Path | str,
    val_fraction: float = 0.2,
    window_size: int = 64,
    step_size: int = 16,
    seed: int = 42,
    include_standby: bool = False,
) -> tuple['''),
    ('''    rng = random.Random(seed)
    spell_classes = list_user_spell_classes(dataset_root)''',
     '''    rng = random.Random(seed)
    spell_classes = list_user_spell_classes(dataset_root, include_standby=include_standby)'''),
])

# ── ml_lab_worker: MlLabTrainWorker + AutoSelectWorker ────────────────
missed += apply("ml_lab/ui/ml_lab_worker.py", [
    ('''        augment_multiplier: int = 1,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.dataset_root = Path(dataset_root)
        self.algo = algo
        self.config = config
        self.feature_config = feature_config or FeatureGroupConfig()
        self.search_config = search_config
        self.val_fraction = val_fraction
        self.augment_multiplier = max(1, int(augment_multiplier))''',
     '''        augment_multiplier: int = 1,
        include_standby: bool = False,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.dataset_root = Path(dataset_root)
        self.algo = algo
        self.config = config
        self.feature_config = feature_config or FeatureGroupConfig()
        self.search_config = search_config
        self.val_fraction = val_fraction
        self.augment_multiplier = max(1, int(augment_multiplier))
        self.include_standby = include_standby'''),
    ('''            train_windows, val_windows, class_names = split_user_dataset_file_level(
                self.dataset_root, val_fraction=self.val_fraction, window_size=64, step_size=16
            )''',
     '''            train_windows, val_windows, class_names = split_user_dataset_file_level(
                self.dataset_root,
                val_fraction=self.val_fraction,
                window_size=64,
                step_size=16,
                include_standby=self.include_standby,
            )'''),
    # AutoSelectWorker
    ('''    def __init__(self, dataset_root: Path | str, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_root = Path(dataset_root)

    def run(self) -> None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._run_inner()''',
     '''    def __init__(self, dataset_root: Path | str, include_standby: bool = False, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_root = Path(dataset_root)
        self.include_standby = include_standby

    def run(self) -> None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._run_inner()'''),
    ('''        train_windows, val_windows, class_names = split_user_dataset_file_level(
            self.dataset_root, val_fraction=0.2, window_size=64, step_size=16
        )''',
     '''        train_windows, val_windows, class_names = split_user_dataset_file_level(
            self.dataset_root,
            val_fraction=0.2,
            window_size=64,
            step_size=16,
            include_standby=self.include_standby,
        )'''),
])

# ── Arena worker ──────────────────────────────────────────────────────
missed += apply("ml_lab/ui/tabs/tab_model_arena.py", [
    ('''    def __init__(self, dataset_dir: Path, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir''',
     '''    def __init__(self, dataset_dir: Path, include_standby: bool = False, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.include_standby = include_standby'''),
    ('''                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir, val_fraction=0.2, window_size=64, step_size=16
                )''',
     '''                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.2,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
                )'''),
])

# ── Curves SweepWorker + DataSizeWorker ───────────────────────────────
missed += apply("ml_lab/ui/tabs/tab_curves_studio.py", [
    ('''    def __init__(self, dataset_dir: Path, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir

    def run(self) -> None:
        try:
            from ml_lab.core.lazy_sklearn import ensure_sklearn

            ensure_sklearn()
            from sklearn.model_selection import StratifiedKFold, cross_val_score  # lazy import''',
     '''    def __init__(self, dataset_dir: Path, include_standby: bool = False, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.include_standby = include_standby

    def run(self) -> None:
        try:
            from ml_lab.core.lazy_sklearn import ensure_sklearn

            ensure_sklearn()
            from sklearn.model_selection import StratifiedKFold, cross_val_score  # lazy import'''),
    ('''                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir, val_fraction=0.01, window_size=64, step_size=16
                )''',
     '''                train_wins, val_wins, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.01,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
                )'''),
    ('''    def __init__(self, dataset_dir: Path, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir

    FRACTIONS''',
     '''    def __init__(self, dataset_dir: Path, include_standby: bool = False, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.include_standby = include_standby

    FRACTIONS'''),
    ('''                train_samples, val_samples, class_names = split_user_dataset_file_level(
                    self.dataset_dir, val_fraction=0.2, window_size=64, step_size=16
                )''',
     '''                train_samples, val_samples, class_names = split_user_dataset_file_level(
                    self.dataset_dir,
                    val_fraction=0.2,
                    window_size=64,
                    step_size=16,
                    include_standby=self.include_standby,
                )'''),
])

print("MISSED TOTAL:", len(missed))
