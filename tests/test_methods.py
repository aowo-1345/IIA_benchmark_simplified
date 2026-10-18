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
