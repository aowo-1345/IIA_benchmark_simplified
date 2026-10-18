import numpy as np
import pandas as pd

from iia_benchmark.tasks.base import BaseTask, TaskResult, reject_overlap
from iia_benchmark.tasks.univariate.contracts import UnivariatePrediction, UnivariateTaskInput
from iia_benchmark.tasks.univariate.methods.factory import create_method
from iia_benchmark.tasks.univariate.metrics import evaluate


def _validate(data):
    design, evaluation = data.design, data.evaluation.segments
    if not design.segments or not evaluation or not design.alarm.source or not np.isfinite(design.alarm.threshold):
        raise ValueError("design/evaluation and finite existing alarm with source required")
    features = design.segments[0].feature_names
    if len(features) != 1 or any(s.feature_names != features for s in design.segments + evaluation):
        raise ValueError("univariate task requires one consistent tag")
    reject_overlap((design.segments, evaluation))
    for segments, references in ((design.segments, design.references), (evaluation, data.references)):
        if len(segments) != len(references):
            raise ValueError("one optional reference required per segment")
        for segment, reference in zip(segments, references, strict=True):
            if reference is not None and len(reference.labels) != len(segment.timestamps):
                raise ValueError("reference length does not match segment")


class UnivariateTask(BaseTask):
    input_type = UnivariateTaskInput

    def __init__(self, parameters):
        super().__init__(parameters)
        self.merge_gap = parameters.get("event_merge_gap_samples", 0)
        if parameters.keys() - {"event_merge_gap_samples"} or not isinstance(self.merge_gap, int) or self.merge_gap < 0:
            raise ValueError("only nonnegative integer event_merge_gap_samples supported")

    def create_method(self, name, parameters):
        return create_method(name, parameters)

    def _baseline(self, data):
        alarm = data.design.alarm
        if data.baseline_replay == "declared_instant_threshold_assumption":
            params = {"threshold": alarm.threshold, "on_delay_seconds": 0., "off_delay_seconds": 0., "deadband": 0.}
        elif data.baseline_replay == "source_settings":
            values = (alarm.on_delay_seconds, alarm.off_delay_seconds, alarm.deadband)
            if any(v is None for v in values):
                raise ValueError("source baseline cannot silently fill missing delay/deadband")
            if alarm.deadband and alarm.deadband_mode is None:
                raise ValueError("source nonzero deadband needs its actual onset/recovery convention")
            params = dict(threshold=alarm.threshold, on_delay_seconds=values[0], off_delay_seconds=values[1], deadband=values[2])
            params["deadband_mode"] = alarm.deadband_mode or "onset_shift"
        else:
            raise ValueError("unsupported baseline replay assumption")
        method = create_method("threshold_rule", params)
        method.design(data.design)
        return method.predict(data.evaluation)

    def run(self, data, method):
        _validate(data)
        baseline = self._baseline(data)
        method.design(data.design)
        prediction = method.predict(data.evaluation)
        segments = data.evaluation.segments
        if not isinstance(prediction, UnivariatePrediction) or len(prediction.detections) != len(segments):
            raise ValueError("method must return one standard detection per segment")
        generated = prediction.evaluation_references or (None,)*len(segments)
        if len(generated) != len(segments):
            raise ValueError("generated reference count mismatch")
        references, frames = [], []
        for i, (segment, detection, base, external, proxy) in enumerate(zip(segments, prediction.detections, baseline.detections,
                                                                          data.references, generated, strict=True)):
            detection.validate_against(segment)
            if proxy is not None and len(proxy.labels) != len(segment.timestamps):
                raise ValueError("generated reference length mismatch")
            reference = external if external is not None else proxy
            references.append(reference)
            frames.append(pd.DataFrame({"segment_id": i, "run_id": segment.run_id, "timestamp": segment.timestamps,
                "source_index": segment.source_indices, "state": detection.state, "baseline_state": base.state,
                "reference_state": reference.labels if reference is not None else -1}))
        metrics, details = evaluate(segments, prediction.detections, baseline.detections, references, self.merge_gap)
        details.update(tag_id=data.design.segments[0].feature_names[0], selected_parameters=prediction.selected_parameters,
            baseline={"policy": data.baseline_replay, "parameters": baseline.selected_parameters},
            reference_policy="external reference object first; otherwise optional method proxy; unknown external points retained",
            reference_details=prediction.reference_details)
        return TaskResult(pd.concat(frames, ignore_index=True), metrics, details)
