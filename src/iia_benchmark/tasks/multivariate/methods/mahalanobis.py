"""Squared Mahalanobis distance, empirical independent-normal quantile cutoff.

Reference: Mahalanobis (1936), reprint doi:10.1007/s13171-019-00164-5.
Ridge regularization/empirical calibration are explicit baseline choices, not
a reproduction of the book's NOZ methods or a Gaussian chi-square guarantee.
"""
import numpy as np

from iia_benchmark.tasks.base import Detection
from iia_benchmark.tasks.multivariate.contracts import MultivariatePrediction
from iia_benchmark.tasks.multivariate.methods.base import MultivariateMethod


class MahalanobisMethod(MultivariateMethod):
    def __init__(self, *, quantile=0.99, ridge=1e-6):
        if not 0 < quantile < 1 or not np.isfinite(ridge) or ridge <= 0:
            raise ValueError("quantile in (0,1) and positive ridge required")
        self.quantile, self.ridge = quantile, ridge
        self.threshold = None

    def _score(self, values):
        centered = values - self.mean
        return np.einsum("ij,jk,ik->i", centered, self.precision, centered)

    def fit(self, data):
        if not data.fit or not data.calibration:
            raise ValueError("Mahalanobis requires normal fit and independent normal calibration")
        values = np.concatenate([s.values for s in data.fit])
        if len(values) < 2:
            raise ValueError("covariance needs at least two fit samples")
        self.mean = values.mean(axis=0)
        covariance = np.atleast_2d(np.cov(values, rowvar=False, ddof=1))
        self.precision = np.linalg.inv(covariance + self.ridge*np.eye(values.shape[1]))
        scores = np.concatenate([self._score(s.values) for s in data.calibration])
        self.threshold = float(np.quantile(scores, self.quantile, method="higher"))

    def predict(self, data):
        if self.threshold is None:
            raise ValueError("fit must precede predict")
        detections = []
        for segment in data.segments:
            score = self._score(segment.values)
            detections.append(Detection(segment.run_id, segment.timestamps.copy(), score > self.threshold, score))
        return MultivariatePrediction(tuple(detections), {"threshold": self.threshold, "quantile": self.quantile,
            "ridge": self.ridge, "mean": self.mean.tolist(), "precision": self.precision.tolist()})
