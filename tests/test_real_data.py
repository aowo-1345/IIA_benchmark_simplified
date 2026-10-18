"""Explicit local acceptance. Missing raw files fail with preparation instructions."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from iia_benchmark.evaluation.binary import confusion, point_metrics
from iia_benchmark.runner import run_experiment

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.real_data


def test_tep_real_pipeline(tmp_path):
    output = run_experiment(ROOT / "configs/experiments/tep_multivariate.json", tmp_path)
    predictions = pd.read_csv(output / "predictions.csv")
    metrics = json.loads((output / "metrics.json").read_text())
    details = json.loads((output / "details.json").read_text())
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "completed" and len(manifest["sources"]) == 3
    assert len(predictions) == 960
    np.testing.assert_array_equal(predictions.source_index, np.arange(960))
    assert (predictions.reference_state == 1).sum() == 800
    recomputed = point_metrics(confusion(predictions.reference_state.to_numpy(), predictions.state.to_numpy(bool)))
    assert all(metrics[k]["value"] == v["value"] for k, v in recomputed.items())
    assert details["references"][0]["scope"] == "process"
    assert set(metrics) == {"F1", "FAR", "MAR", "ADD"}


def test_power_plant_real_search(tmp_path):
    output = run_experiment(ROOT / "configs/experiments/power_plant_pressure_univariate.json", tmp_path)
    predictions = pd.read_csv(output / "predictions.csv")
    metrics = json.loads((output / "metrics.json").read_text())
    details = json.loads((output / "details.json").read_text())
    assert len(predictions) == 2678400-484984
    assert predictions.source_index.iloc[0] == 484984
    assert predictions.source_index.iloc[-1] == 2678399
    assert set(metrics) == {"F1", "FAR", "MAR", "ADD", "alarm_compression_rate"}
    for key in ("F1", "FAR", "MAR"):
        assert metrics[key]["status"] == "available"
    recomputed = point_metrics(confusion(predictions.reference_state.to_numpy(), predictions.state.to_numpy(bool)))
    assert all(metrics[k]["value"] == v["value"] for k, v in recomputed.items())
    assert 0 < details["reference_details"]["design_search"]["evaluated"] <= 36
    assert "statistical_proxy" in details["references"][0]["source"]
    assert details["baseline"]["policy"] == "declared_instant_threshold_assumption"
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "completed" and len(manifest["sources"]) == 1
