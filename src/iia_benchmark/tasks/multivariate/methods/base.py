from abc import ABC, abstractmethod

from iia_benchmark.tasks.multivariate.contracts import (
    MultivariateEvaluationView, MultivariatePrediction, MultivariateTrainingView,
)


class MultivariateMethod(ABC):
    @abstractmethod
    def fit(self, data: MultivariateTrainingView) -> None:
        """Fit/calibrate only with the allowed normal training view."""

    @abstractmethod
    def predict(self, data: MultivariateEvaluationView) -> MultivariatePrediction:
        """Return states aligned to all segments; no evaluation labels supplied."""
