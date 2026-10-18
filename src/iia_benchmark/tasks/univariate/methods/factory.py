from iia_benchmark.tasks.univariate.methods.base import UnivariateMethod
from iia_benchmark.tasks.univariate.methods.threshold_rule import ThresholdRuleMethod
from iia_benchmark.tasks.univariate.methods.non_iid_search import NonIIDSearchMethod

METHODS = {"threshold_rule": ThresholdRuleMethod, "non_iid_threshold_delay_search": NonIIDSearchMethod}


def create_method(name, parameters):
    if name not in METHODS:
        raise ValueError(f"unsupported univariate method {name!r}")
    method = METHODS[name](**parameters)
    if not isinstance(method, UnivariateMethod):
        raise TypeError("registered method must implement UnivariateMethod")
    return method
