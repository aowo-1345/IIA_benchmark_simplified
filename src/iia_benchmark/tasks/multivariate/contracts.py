from dataclasses import dataclass, field

from iia_benchmark.tasks.base import Detection, Reference, SignalSegment


@dataclass(frozen=True)
class MultivariateTrainingView:
    fit: tuple[SignalSegment, ...]
    calibration: tuple[SignalSegment, ...] = ()


@dataclass(frozen=True)
class MultivariateEvaluationView:
    segments: tuple[SignalSegment, ...]


@dataclass(frozen=True)
class MultivariateTaskInput:
    training: MultivariateTrainingView
    evaluation: MultivariateEvaluationView
    references: tuple[Reference | None, ...]
    normal_basis: str
    group_id: str


@dataclass(frozen=True)
class MultivariatePrediction:
    detections: tuple[Detection, ...]
    parameters: dict = field(default_factory=dict)
