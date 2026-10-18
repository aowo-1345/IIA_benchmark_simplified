"""Experiment references use project-root paths; task adapter refs use dataset dir."""
from dataclasses import dataclass
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class ExperimentPlan:
    root: Path
    snapshot: dict
    config_paths: dict[str, str]


def project_root(path: Path) -> Path:
    for parent in (path.parent, *path.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    raise ValueError(f"cannot locate project pyproject.toml from {path}")


def _read(path, required, allowed):
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - allowed:
        raise ValueError(f"invalid fields in {path}; required={sorted(required)}, allowed={sorted(allowed)}")
    return value


def load_experiment(path: str | Path) -> ExperimentPlan:
    path = Path(path).resolve()
    root = project_root(path)
    experiment = _read(path, {"name", "dataset", "task", "model"}, {"name", "dataset", "task", "model"})
    if not isinstance(experiment["name"], str) or not re.fullmatch(r"[A-Za-z0-9_-]+", experiment["name"]):
        raise ValueError("experiment name must contain only letters, digits, underscore or hyphen")
    paths = {"experiment": str(path)}
    snapshot = {"experiment": experiment}
    specs = {
        "dataset": {"id", "adapter", "adapter_config", "task_adapters"},
        "task": {"kind", "parameters"},
        "model": {"method", "parameters"},
    }
    for key, fields in specs.items():
        ref = (root / experiment[key]).resolve()
        snapshot[key] = _read(ref, fields, fields)
        paths[key] = str(ref)
    dataset, task = snapshot["dataset"], snapshot["task"]
    if task["kind"] not in dataset["task_adapters"]:
        raise ValueError(f"dataset {dataset['id']} does not support task {task['kind']}")
    ref = (Path(paths["dataset"]).parent / dataset["task_adapters"][task["kind"]]).resolve()
    fields = {"dataset_id", "task_kind", "adapter", "adapter_config"}
    adapter = _read(ref, fields, fields)
    if adapter["dataset_id"] != dataset["id"] or adapter["task_kind"] != task["kind"]:
        raise ValueError("Task Adapter dataset/task identity mismatch")
    snapshot["task_adapter"] = adapter
    paths["task_adapter"] = str(ref)
    return ExperimentPlan(root, snapshot, paths)
