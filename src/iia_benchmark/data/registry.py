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


BUNDLE_ADAPTERS: dict[str, Callable[[dict, SourceContext], DatasetBundle]] = {}
TASK_ADAPTERS: dict[str, TaskAdapter] = {}


def get_bundle_adapter(name):
    if name not in BUNDLE_ADAPTERS:
        raise ValueError(f"unsupported Bundle Adapter {name!r}")
    return BUNDLE_ADAPTERS[name]


def get_task_adapter(name):
    if name not in TASK_ADAPTERS:
        raise ValueError(f"unsupported Task Adapter {name!r}")
    return TASK_ADAPTERS[name]
