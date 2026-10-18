from dataclasses import dataclass, field

from iia_benchmark.tasks.base import Detection, Reference, SignalSegment


@dataclass(frozen=True)
class AlarmSetting:
    """Existing source facts, not a fully specified replay rule. None != zero."""
    direction: str
    threshold: float
    source: str
    on_delay_seconds: float | None = None
    off_delay_seconds: float | None = None
    deadband: float | None = None
    deadband_mode: str | None = None


@dataclass(frozen=True)
class UnivariateDesignView:
    segments: tuple[SignalSegment, ...]
    alarm: AlarmSetting
    references: tuple[Reference | None, ...]


@dataclass(frozen=True)
class UnivariateEvaluationView:
    segments: tuple[SignalSegment, ...]


@dataclass(frozen=True)
class UnivariateTaskInput:
    design: UnivariateDesignView
    evaluation: UnivariateEvaluationView
    references: tuple[Reference | None, ...]
    baseline_replay: str


@dataclass(frozen=True)
class UnivariatePrediction:
    detections: tuple[Detection, ...]
    selected_parameters: dict
    # Optional method-generated evaluation reference, aligned per input segment.
    # Used only for a segment with no external reference object. If an external
    # reference is partially unknown, retain it intact; do not fill unknown points
    # from this method's proxy. Always disclose the source,
    # scope and assumptions. Fixed/other methods need not generate any reference.
    # These are materials for Task scoring, NEVER final Method-reported metrics.
    evaluation_references: tuple[Reference | None, ...] = ()
    reference_details: dict = field(default_factory=dict)
