"""Common scheduling/result envelope; task-specific learning remains separate."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SignalSegment:
    """One uninterrupted interval, values [N,D], time in seconds.

    source_indices are zero-based sample positions within the original run,
    NOT physical row positions in the long process_values table. Together with
    run_id and feature_names they map each output row/column back to its source.
    Missing/invalid samples or time gaps must break segments before this point.
    """

    run_id: str
    timestamps: np.ndarray
    values: np.ndarray
    source_indices: np.ndarray
    feature_names: tuple[str, ...]

    def __post_init__(self):
        n = len(self.timestamps)
        if not n or not self.run_id or not self.feature_names or self.values.shape != (n, len(self.feature_names)):
            raise ValueError("segment values must be nonempty [N,D]")
        if self.timestamps.shape != (n,) or self.source_indices.shape != (n,):
            raise ValueError("segment time/source mapping must be [N]")
        if not np.issubdtype(self.source_indices.dtype, np.integer) or np.any(self.source_indices < 0):
            raise ValueError("source indices must be nonnegative integers")
        if not np.isfinite(self.values).all() or not np.isfinite(self.timestamps).all():
            raise ValueError("segments contain only finite, valid samples")
        if np.any(np.diff(self.timestamps) <= 0) or np.any(np.diff(self.source_indices) != 1):
            raise ValueError("segment must preserve increasing time and consecutive source rows")
        if len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("duplicate feature names")


@dataclass(frozen=True)
class Reference:
    """Task-owned labels: -1 unknown, 0 normal, 1 abnormal; never Method input."""

    labels: np.ndarray
    source: str
    scope: str

    def __post_init__(self):
        if self.labels.ndim != 1 or not np.isin(self.labels, [-1, 0, 1]).all():
            raise ValueError("reference labels must be a vector of -1/0/1")
        if not self.source or not self.scope:
            raise ValueError("reference requires source and scope")


@dataclass(frozen=True)
class Detection:
    run_id: str
    timestamps: np.ndarray
    state: np.ndarray
    score: np.ndarray | None = None

    def validate_against(self, segment: SignalSegment):
        if self.run_id != segment.run_id or not np.array_equal(self.timestamps, segment.timestamps):
            raise ValueError("prediction run/time does not match its input segment")
        if self.state.shape != self.timestamps.shape or self.state.dtype != np.dtype(bool):
            raise ValueError("prediction state must be a boolean vector matching input")
        if self.score is not None and (self.score.shape != self.state.shape or not np.isfinite(self.score).all()):
            raise ValueError("optional scores must be finite and match input")


@dataclass
class TaskResult:
    predictions: pd.DataFrame
    metrics: dict
    details: dict = field(default_factory=dict)


class BaseTask(ABC):
    input_type: type

    def __init__(self, parameters: dict):
        self.parameters = parameters

    @abstractmethod
    def create_method(self, name: str, parameters: dict):
        """Reject methods outside this task before loading source data."""

    @abstractmethod
    def run(self, data, method) -> TaskResult:
        """Validate task data, call its Method protocol, then score standard results."""
