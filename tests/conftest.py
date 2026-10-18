import numpy as np
import pytest

from iia_benchmark.tasks.base import Reference, SignalSegment
from iia_benchmark.tasks.univariate.contracts import (
    AlarmSetting, UnivariateDesignView, UnivariateEvaluationView, UnivariateTaskInput,
)


@pytest.fixture
def univariate_input():
    def make(values, labels=None, direction="high", design_values=(8., 9., 11., 12.)):
        def segment(run, points):
            return SignalSegment(run, np.arange(len(points), dtype=float), np.asarray(points, float).reshape(-1, 1),
                                 np.arange(len(points)), ("x",))
        return UnivariateTaskInput(UnivariateDesignView((segment("design", design_values),),
            AlarmSetting(direction, 10., "test existing alarm"), (None,)),
            UnivariateEvaluationView((segment("evaluation", values),)),
            (Reference(np.array(labels), "test external", "tag") if labels is not None else None,),
            "declared_instant_threshold_assumption")
    return make
