"""Test-only components exercise the real loader/registries/Runner/writer."""
import json

import numpy as np
import pandas as pd
import pytest

from iia_benchmark.config.loader import load_experiment
from iia_benchmark.data.contracts import DatasetBundle
from iia_benchmark.data.registry import BUNDLE_ADAPTERS, TASK_ADAPTERS, TaskAdapter
from iia_benchmark.runner import run_experiment
from iia_benchmark.tasks.base import BaseTask, Detection, Reference, SignalSegment, TaskResult
from iia_benchmark.tasks.factory import TASKS
from iia_benchmark.tasks.multivariate.contracts import (
    MultivariateEvaluationView, MultivariatePrediction, MultivariateTaskInput, MultivariateTrainingView,
)
from iia_benchmark.tasks.multivariate.methods.base import MultivariateMethod


class ConstantMethod(MultivariateMethod):
    def __init__(self, value=False):
        self.value = value

    def fit(self, data):
        assert isinstance(data, MultivariateTrainingView)
        assert not hasattr(data, "references")

    def predict(self, data):
        assert isinstance(data, MultivariateEvaluationView)
        assert not hasattr(data, "references")
        return MultivariatePrediction(tuple(
            Detection(s.run_id, s.timestamps.copy(), np.full(len(s.timestamps), self.value, dtype=bool))
            for s in data.segments
        ))


class ExampleTask(BaseTask):
    input_type = MultivariateTaskInput

    def create_method(self, name, parameters):
        if name != "constant":
            raise ValueError("unsupported method")
        return ConstantMethod(**parameters)

    def run(self, data, method):
        method.fit(data.training)
        prediction = method.predict(data.evaluation)
        rows = []
        for segment, detection in zip(data.evaluation.segments, prediction.detections, strict=True):
            detection.validate_against(segment)
            rows.extend({"run_id": segment.run_id, "timestamp": t, "state": bool(a)}
                        for t, a in zip(detection.timestamps, detection.state, strict=True))
        return TaskResult(pd.DataFrame(rows), {"test_only": {"status": "unavailable", "reason": "T1 plumbing"}})


@pytest.fixture
def example(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='sample'\n")
    (tmp_path / "source.csv").write_text("timestamp,x\n0,1\n1,2\n2,3\n3,4\n")
    configs = {
        "experiment.json": {"name": "sample", "dataset": "dataset.json", "task": "task.json", "model": "model.json"},
        "dataset.json": {"id": "sample", "adapter": "sample.csv", "adapter_config": {"path": "source.csv"},
                         "task_adapters": {"sample_task": "conversion.json"}},
        "conversion.json": {"dataset_id": "sample", "task_kind": "sample_task", "adapter": "sample.convert", "adapter_config": {}},
        "task.json": {"kind": "sample_task", "parameters": {}},
        "model.json": {"method": "constant", "parameters": {}},
    }
    for name, content in configs.items():
        (tmp_path / name).write_text(json.dumps(content))

    def load(config, context):
        frame = pd.read_csv(context.file(config["path"]))
        return DatasetBundle(pd.DataFrame({"timestamp": frame.timestamp, "value": frame.x,
                                          "run_id": "r", "tag_id": "x", "quality_flag": True}))

    def prepare(bundle, config):
        frame = bundle.process_values
        def segment(start, stop):
            part = frame.iloc[start:stop]
            return SignalSegment("r", part.timestamp.to_numpy(float), part[["value"]].to_numpy(float),
                                 np.arange(start, stop), ("x",))
        return MultivariateTaskInput(MultivariateTrainingView((segment(0, 2),)),
                                     MultivariateEvaluationView((segment(2, 4),)),
                                     (Reference(np.array([-1, 1]), "test source", "process"),), "test normal", "g")

    monkeypatch.setitem(BUNDLE_ADAPTERS, "sample.csv", load)
    monkeypatch.setitem(TASK_ADAPTERS, "sample.convert", TaskAdapter("sample_task", MultivariateTaskInput, prepare))
    monkeypatch.setitem(TASKS, "sample_task", ExampleTask)
    return tmp_path


def test_config_to_result_and_independent_runs(example):
    path = example / "experiment.json"
    first = run_experiment(path)
    second = run_experiment(path)
    assert first != second
    assert first.parent.name == "sample"
    assert json.loads((first / "config.snapshot.json").read_text())["task_adapter"]["dataset_id"] == "sample"
    manifest = json.loads((first / "manifest.json").read_text())
    assert manifest["status"] == "completed"
    assert manifest["sources"][str(example / "source.csv")]["bytes"] > 0
    assert pd.read_csv(first / "predictions.csv").timestamp.tolist() == [2.0, 3.0]
    old_snapshot = (first / "config.snapshot.json").read_bytes()
    (example / "model.json").write_text(json.dumps({"method": "constant", "parameters": {"value": True}}))
    third = run_experiment(path)
    assert pd.read_csv(third / "predictions.csv").state.all()
    assert (first / "config.snapshot.json").read_bytes() == old_snapshot


def test_unsupported_and_mismatched_config_fails_before_loading(example):
    (example / "task.json").write_text(json.dumps({"kind": "other", "parameters": {}}))
    with pytest.raises(ValueError, match="does not support"):
        load_experiment(example / "experiment.json")
    (example / "task.json").write_text(json.dumps({"kind": "sample_task", "parameters": {}}))
    adapter = json.loads((example / "conversion.json").read_text())
    adapter["dataset_id"] = "wrong"
    (example / "conversion.json").write_text(json.dumps(adapter))
    with pytest.raises(ValueError, match="identity mismatch"):
        run_experiment(example / "experiment.json")


def test_missing_source_records_failed_run(example):
    (example / "source.csv").unlink()
    with pytest.raises(FileNotFoundError, match="data/README.md"):
        run_experiment(example / "experiment.json")
    manifest = next((example / "experiments/runs").rglob("manifest.json"))
    assert json.loads(manifest.read_text())["status"] == "failed"


def test_prediction_cannot_change_alignment_or_emit_nan():
    segment = SignalSegment("r", np.array([0., 1.]), np.ones((2, 1)), np.arange(2), ("x",))
    with pytest.raises(ValueError, match="run/time"):
        Detection("other", segment.timestamps, np.zeros(2, bool)).validate_against(segment)
    with pytest.raises(ValueError, match="scores"):
        Detection("r", segment.timestamps, np.zeros(2, bool), np.array([0., np.nan])).validate_against(segment)
