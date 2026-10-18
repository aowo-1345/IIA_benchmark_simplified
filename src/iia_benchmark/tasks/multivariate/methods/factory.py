from iia_benchmark.tasks.multivariate.methods.mahalanobis import MahalanobisMethod
from iia_benchmark.tasks.multivariate.methods.base import MultivariateMethod

METHODS = {"mahalanobis": MahalanobisMethod}


def create_method(name, parameters):
    if name not in METHODS:
        raise ValueError(f"unsupported multivariate method {name!r}")
    method = METHODS[name](**parameters)
    if not isinstance(method, MultivariateMethod):
        raise TypeError("registered method must implement MultivariateMethod")
    return method
