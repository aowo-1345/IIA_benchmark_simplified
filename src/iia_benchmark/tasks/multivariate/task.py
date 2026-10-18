import numpy as np
import pandas as pd

from iia_benchmark.tasks.base import BaseTask, TaskResult, reject_overlap
from iia_benchmark.tasks.multivariate.contracts import MultivariatePrediction, MultivariateTaskInput
from iia_benchmark.tasks.multivariate.methods.factory import create_method
from iia_benchmark.tasks.multivariate.metrics import evaluate


class MultivariateTask(BaseTask):
    input_type = MultivariateTaskInput

    def __init__(self, parameters):
        super().__init__(parameters)
        if parameters:
            raise ValueError("multivariate task currently has no configurable parameters")

    def create_method(self, name, parameters):
        return create_method(name, parameters)

    def run(self, data, method):
        train, evaluation = data.training, data.evaluation.segments
        if not train.fit or not evaluation or not data.normal_basis:
            raise ValueError("fit, evaluation and explicit normal basis required")
        if len(data.references) != len(evaluation):
            raise ValueError("one optional reference required per evaluation segment")
        features = train.fit[0].feature_names
        if any(s.feature_names != features for s in train.fit + train.calibration + evaluation):
            raise ValueError("feature order must match across roles")
        reject_overlap((train.fit, train.calibration, evaluation))
        for segment, ref in zip(evaluation, data.references, strict=True):
            if ref is not None and len(ref.labels) != len(segment.timestamps):
                raise ValueError("reference length does not match segment")
        method.fit(train)
        prediction = method.predict(data.evaluation)
        if not isinstance(prediction, MultivariatePrediction) or len(prediction.detections) != len(evaluation):
            raise ValueError("method must return one standard detection per segment")
        frames = []
        for i, (segment, detection, ref) in enumerate(zip(evaluation, prediction.detections, data.references, strict=True)):
            detection.validate_against(segment)
            frames.append(pd.DataFrame({"segment_id": i, "run_id": segment.run_id, "timestamp": segment.timestamps,
                "source_index": segment.source_indices, "state": detection.state,
                "score": detection.score if detection.score is not None else np.nan,
                "reference_state": ref.labels if ref is not None else -1}))
        metrics, details = evaluate(evaluation, prediction.detections, data.references)
        details.update(group_id=data.group_id, feature_names=list(features), normal_basis=data.normal_basis,
                       selected_parameters=prediction.parameters)
        return TaskResult(pd.concat(frames, ignore_index=True), metrics, details)
