"""
logic/dataset_auditor.py — Core logic for analyzing dataset health and quality.

Checks for:
    - Class imbalance (too many/few samples per gesture)
    - Sample quality (length, variance/noise, clipping)
    - Potential outliers within a class
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .dataset_layout import discover_class_directories

@dataclass
class SampleAudit:
    file_path: str
    spell_name: str
    length: int
    variance: float
    is_clipping: bool
    is_too_short: bool
    is_too_long: bool
    is_flat: bool
    score: float = 1.0  # 0.0 (bad) to 1.0 (good)

@dataclass
class ClassAudit:
    spell_name: str
    sample_count: int
    avg_length: float
    avg_variance: float
    imbalance_ratio: float = 1.0  # Ratio to dataset average
    status: str = "OK"  # "OK", "IMBALANCED", "EMPTY", "HEALTHY"
    samples: List[SampleAudit] = field(default_factory=list)

@dataclass
class DatasetReport:
    total_samples: int
    class_audits: Dict[str, ClassAudit]
    imbalanced_classes: List[str]
    outlier_samples: List[SampleAudit]
    system_health_score: float  # 0-100

class DatasetAuditor:
    """Performs deep analysis of the CSV dataset files."""

    def __init__(self, dataset_dir: str):
        self.dataset_dir = Path(dataset_dir)
        self.min_length = 20  # ~400ms at 50Hz
        self.max_length = 200 # ~4s
        self.min_variance = 0.001 # Flat detection

    def run_audit(self) -> DatasetReport:
        """Execute full scan of the dataset directory."""
        if not self.dataset_dir.exists():
            return DatasetReport(0, {}, [], [], 0.0)

        class_audits: Dict[str, ClassAudit] = {}
        all_samples: List[SampleAudit] = []
        
        class_dir_map = discover_class_directories(self.dataset_dir)

        # 1. Individual sample analysis
        for spell_name in sorted(class_dir_map.keys()):
            csv_files: list[Path] = []
            for d in class_dir_map[spell_name]:
                csv_files.extend(sorted(d.glob("*.csv")))
            csv_files.sort(key=lambda p: p.as_posix())

            current_class_audit = ClassAudit(
                spell_name=spell_name,
                sample_count=len(csv_files),
                avg_length=0,
                avg_variance=0,
            )

            lengths = []
            variances = []

            for csv_file in csv_files:
                sample_audit = self.audit_sample(csv_file, spell_name)
                current_class_audit.samples.append(sample_audit)
                all_samples.append(sample_audit)
                lengths.append(sample_audit.length)
                variances.append(sample_audit.variance)

            if lengths:
                current_class_audit.avg_length = float(np.mean(lengths))
                current_class_audit.avg_variance = float(np.mean(variances))

            class_audits[spell_name] = current_class_audit

        # 2. Dataset-wide imbalance check
        counts = [a.sample_count for a in class_audits.values() if a.sample_count > 0]
        avg_count = np.mean(counts) if counts else 0
        
        imbalanced_classes = []
        for audit in class_audits.values():
            if avg_count > 0:
                audit.imbalance_ratio = audit.sample_count / avg_count
                if audit.imbalance_ratio < 0.5:
                    audit.status = "LOW_DATA"
                    imbalanced_classes.append(audit.spell_name)
                elif audit.imbalance_ratio > 2.0:
                    audit.status = "OVER_REPRESENTED"
                    imbalanced_classes.append(audit.spell_name)

        # 3. Identify outliers (simple variance-based for now)
        outliers = [s for s in all_samples if s.is_too_short or s.is_flat or s.is_clipping]

        # 4. Calculate health score
        health_score = 100.0
        if avg_count < 10: health_score -= 20
        health_score -= len(imbalanced_classes) * 5
        health_score -= len(outliers) * 2
        health_score = max(0, min(100, health_score))

        return DatasetReport(
            total_samples=len(all_samples),
            class_audits=class_audits,
            imbalanced_classes=imbalanced_classes,
            outlier_samples=outliers,
            system_health_score=health_score
        )

    def audit_sample(self, file_path: Path, spell_name: str) -> SampleAudit:
        """Analyze a single CSV file for quality issues."""
        rows = []
        try:
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                next(reader) # skip header
                for row in reader:
                    if len(row) >= 6:
                        rows.append([float(x) for x in row[:6]])
        except Exception:
            return SampleAudit(str(file_path), spell_name, 0, 0, False, True, False, True, 0.0)

        data = np.array(rows)
        length = len(data)
        
        if length == 0:
            return SampleAudit(str(file_path), spell_name, 0, 0, False, True, False, True, 0.0)

        # Variance check (across all axes)
        var = float(np.mean(np.var(data, axis=0)))
        
        # Clipping check (assume normalized -1.0 to 1.0 or similar)
        is_clipping = bool(np.any(np.abs(data) >= 1.95)) # Threshold near 2.0 (scaled)
        
        is_too_short = length < self.min_length
        is_too_long = length > self.max_length
        is_flat = var < self.min_variance
        
        # Heuristic score
        score = 1.0
        if is_too_short: score -= 0.5
        if is_flat: score -= 0.8
        if is_clipping: score -= 0.3
        score = max(0.0, score)

        return SampleAudit(
            file_path=str(file_path),
            spell_name=spell_name,
            length=length,
            variance=var,
            is_clipping=is_clipping,
            is_too_short=is_too_short,
            is_too_long=is_too_long,
            is_flat=is_flat,
            score=score
        )
