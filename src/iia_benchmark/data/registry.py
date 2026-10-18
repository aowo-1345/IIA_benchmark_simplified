"""Explicit adapter registration and source auditing, independent of the Runner."""
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Callable

from iia_benchmark.data.contracts import DatasetBundle


@dataclass
class SourceContext:
    root: Path
    sources: dict = field(default_factory=dict)

    def file(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Missing source {path}; prepare data per data/README.md")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        self.sources[str(path)] = {"bytes": path.stat().st_size, "sha256": digest}
        return path


@dataclass(frozen=True)
class TaskAdapter:
    task_kind: str
    input_type: type
    prepare: Callable


from iia_benchmark.data.datasets.tep.bundle import load_bundle as tep_bundle
from iia_benchmark.data.datasets.tep.task_adapters.multivariate import prepare as tep_multivariate
from iia_benchmark.tasks.multivariate.contracts import MultivariateTaskInput
from iia_benchmark.data.datasets.power_plant.bundle import load_bundle as power_plant_bundle
from iia_benchmark.data.datasets.power_plant.task_adapters.univariate import prepare as power_plant_univariate
from iia_benchmark.tasks.univariate.contracts import UnivariateTaskInput

BUNDLE_ADAPTERS: dict[str, Callable[[dict, SourceContext], DatasetBundle]] = {
    "tep.bundle": tep_bundle, "power_plant.bundle": power_plant_bundle,
}
TASK_ADAPTERS: dict[str, TaskAdapter] = {
    "tep.multivariate": TaskAdapter("multivariate_detection", MultivariateTaskInput, tep_multivariate),
    "power_plant.univariate": TaskAdapter("univariate_detection", UnivariateTaskInput, power_plant_univariate),
}


def get_bundle_adapter(name):
    if name not in BUNDLE_ADAPTERS:
        raise ValueError(f"unsupported Bundle Adapter {name!r}")
    return BUNDLE_ADAPTERS[name]


def get_task_adapter(name):
    if name not in TASK_ADAPTERS:
        raise ValueError(f"unsupported Task Adapter {name!r}")
    return TASK_ADAPTERS[name]
