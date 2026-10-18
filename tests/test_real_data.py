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
