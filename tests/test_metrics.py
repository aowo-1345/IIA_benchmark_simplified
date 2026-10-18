import numpy as np
import pytest

from iia_benchmark.evaluation.binary import confusion, point_metrics
from iia_benchmark.evaluation.events import detection_delays


def test_known_point_denominators_and_unknown_exclusion():
    c = confusion(np.array([0, 0, 1, 1, -1]), np.array([0, 1, 1, 0, 1], bool))
    assert c == {"tp": 1, "fn": 1, "fp": 1, "tn": 1, "unknown": 1}
    assert {k: v["value"] for k, v in point_metrics(c).items()} == {"F1": .5, "FAR": .5, "MAR": .5}
    normal = point_metrics(confusion(np.array([0, 0]), np.array([0, 0], bool)))
    assert normal["FAR"]["value"] == 0
    assert normal["MAR"]["status"] == normal["F1"]["status"] == "unavailable"
    unknown = point_metrics(confusion(np.array([-1]), np.array([1], bool)))
    assert all(m["value"] is None for m in unknown.values())


def test_delay_seconds_misses_and_left_censoring():
    labels = np.array([1, 0, 1, 1, 0, 1, 1, -1, 1])
    state = np.array([0, 0, 0, 1, 0, 0, 0, 0, 1], bool)
    delays, missed, censored = detection_delays(np.arange(9)*3., labels, state)
    assert delays == [3.]
    assert missed == 1
    assert censored == 2
    # Separate call/segment must not inherit the preceding normal observation.
    assert detection_delays(np.array([100., 103.]), np.array([1, 1]), np.array([1, 1], bool)) == ([], 0, 1)


def test_univariate_fixed_replay_scores_and_zero_baseline(univariate_input):
    from iia_benchmark.tasks.univariate.task import UnivariateTask
    task = UnivariateTask({})
    data = univariate_input([9, 11, 9, 11, 11, 9], [0, 0, 0, 1, 1, 0])
    result = task.run(data, task.create_method("threshold_rule", {"on_delay_seconds": 1, "off_delay_seconds": 1}))
    assert {k: v["value"] for k, v in result.metrics.items()} == {
        "F1": .5, "FAR": .25, "MAR": .5, "ADD": 1., "alarm_compression_rate": .5}
    assert result.details["alarm_events"] == {"baseline": 2, "candidate": 1, "merge_gap_samples": 0}
    empty = task.run(univariate_input([8, 8, 8]), task.create_method("threshold_rule", {}))
    assert empty.metrics["alarm_compression_rate"]["status"] == "unavailable"
    assert empty.metrics["FAR"]["status"] == "unavailable"  # No truth: not silently normal.


def test_external_unknown_reference_is_not_filled_by_method_proxy(univariate_input):
    from dataclasses import replace
    from iia_benchmark.tasks.base import Reference
    from iia_benchmark.tasks.univariate.methods.threshold_rule import ThresholdRuleMethod
    from iia_benchmark.tasks.univariate.task import UnivariateTask
    class ProxyMethod(ThresholdRuleMethod):
        def predict(self, view):
            result = super().predict(view)
            return replace(result, evaluation_references=(Reference(np.ones(len(view.segments[0].timestamps)), "test proxy", "tag"),))
    task = UnivariateTask({})
    result = task.run(univariate_input([11, 11], [-1, 0]), ProxyMethod())
    assert result.predictions.reference_state.tolist() == [-1, 0]
    assert result.details["references"][0]["source"] == "test external"
    assert result.metrics["F1"]["value"] is None
