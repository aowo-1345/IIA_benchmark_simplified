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
