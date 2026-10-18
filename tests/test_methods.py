import numpy as np
import pytest

from iia_benchmark.tasks.base import SignalSegment
from iia_benchmark.tasks.multivariate.contracts import MultivariateEvaluationView, MultivariateTrainingView
from iia_benchmark.tasks.multivariate.methods.mahalanobis import MahalanobisMethod


def test_mahalanobis_matches_hand_covariance_and_calibration():
    def segment(run, values):
        values = np.asarray(values, float)
        return SignalSegment(run, np.arange(len(values), dtype=float), values, np.arange(len(values)), ("x", "y"))
    fit = segment("fit", [[-1, 0], [1, 0], [0, -1], [0, 1]])
    calibration = segment("cal", [[0, 0], [1, 0], [2, 0]])
    evaluation = MultivariateEvaluationView((segment("eval", [[1, 0], [2, 0]]),))
    method = MahalanobisMethod(ridge=1., quantile=0.5)
    with pytest.raises(ValueError, match="fit must"):
        method.predict(evaluation)
    method.fit(MultivariateTrainingView((fit,), (calibration,)))
    result = method.predict(evaluation)
    # Sample covariance is (2/3)I, ridge gives (5/3)I, inverse is (3/5)I.
    np.testing.assert_allclose(result.detections[0].score, [.6, 2.4])
    assert result.parameters["threshold"] == pytest.approx(.6)
    assert result.detections[0].state.tolist() == [False, True]


@pytest.mark.parametrize("direction,values", [
    ("high", [10, 12, 12, 11, 10, 9, 9, 12]),
    ("low", [10, 8, 8, 9, 10, 11, 11, 8]),
])
def test_delay_deadband_boundaries_and_segment_reset(univariate_input, direction, values):
    from dataclasses import replace
    from iia_benchmark.tasks.univariate.methods.threshold_rule import ThresholdRuleMethod
    data = univariate_input(values, direction=direction)
    method = ThresholdRuleMethod(on_delay_seconds=1, off_delay_seconds=1, deadband=2)
    method.design(data.design)
    result = method.predict(data.evaluation)
    assert result.detections[0].state.tolist() == [False, False, True, True, True, True, False, False]
    assert result.evaluation_references == ()
    tail = data.evaluation.segments[0]
    hold = 11 if direction == "high" else 9
    tail = replace(tail, values=np.full_like(tail.values, hold))
    reset = method.predict(replace(data.evaluation, segments=(tail,)))
    assert not reset.detections[0].state.any()
    immediate = ThresholdRuleMethod()
    immediate.design(data.design)
    assert immediate.predict(data.evaluation).detections[0].state[0]  # equality triggers with zero band/delay


def test_delay_is_elapsed_seconds_not_sample_count(univariate_input):
    from dataclasses import replace
    from iia_benchmark.tasks.univariate.methods.threshold_rule import ThresholdRuleMethod
    data = univariate_input([12, 12, 12, 12])
    segment = replace(data.evaluation.segments[0], timestamps=np.array([0., .5, 1.5, 2.]))
    method = ThresholdRuleMethod(on_delay_seconds=1.)
    method.design(data.design)
    assert method.predict(replace(data.evaluation, segments=(segment,))).detections[0].state.tolist() == [False, False, True, True]


def test_recovery_shift_is_explicit_and_source_baseline_cannot_invent_it(univariate_input):
    from dataclasses import replace
    from iia_benchmark.tasks.univariate.task import UnivariateTask
    task = UnivariateTask({})
    data = univariate_input([10, 9, 8, 7, 9])
    method = task.create_method("threshold_rule", {"deadband": 2, "deadband_mode": "recovery_shift"})
    result = task.run(data, method)
    assert result.predictions.state.tolist() == [True, True, True, False, False]
    source = replace(data, baseline_replay="source_settings")
    with pytest.raises(ValueError, match="missing delay"):
        task.run(source, method)
    alarm = replace(data.design.alarm, on_delay_seconds=0, off_delay_seconds=0, deadband=2)
    source = replace(source, design=replace(data.design, alarm=alarm))
    with pytest.raises(ValueError, match="convention"):
        task.run(source, method)
