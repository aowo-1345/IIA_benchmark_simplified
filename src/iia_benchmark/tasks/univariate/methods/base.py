from abc import ABC, abstractmethod

from iia_benchmark.tasks.univariate.contracts import (
    UnivariateDesignView, UnivariateEvaluationView, UnivariatePrediction,
)


class UnivariateMethod(ABC):
    @abstractmethod
    def design(self, data: UnivariateDesignView) -> None:
        """Configure/fit using allowed design data, then freeze chosen parameters."""

    @abstractmethod
    def predict(self, data: UnivariateEvaluationView) -> UnivariatePrediction:
        """Return aligned alarm states; t tests are NOT a task requirement."""
