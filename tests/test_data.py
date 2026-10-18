import numpy as np
import pandas as pd
import pytest

from iia_benchmark.data.contracts import DatasetBundle
from iia_benchmark.data.datasets.tep.bundle import load_bundle
from iia_benchmark.data.datasets.tep.task_adapters.multivariate import prepare
from iia_benchmark.data.registry import SourceContext


def test_four_table_facts_reject_ambiguous_keys_and_references():
    frame = pd.DataFrame({"run_id": ["r", "r"], "timestamp": [0., 1.], "tag_id": "x",
                          "value": [1., np.nan], "quality_flag": [True, False]})
    bundle = DatasetBundle(frame)
    assert set(vars(bundle)) == {"process_values", "tag_alarm_settings", "variable_groups", "status_events"}
    assert bundle.status_events.empty  # Absence is unknown, not an inferred normal event.
    with pytest.raises(ValueError, match="unique"):
        DatasetBundle(pd.concat([frame, frame.iloc[:1]], ignore_index=True))
    with pytest.raises(ValueError, match="unknown tag"):
        DatasetBundle(frame, variable_groups=pd.DataFrame({"group_id": ["g"], "tag_id": ["missing"]}))
    with pytest.raises(ValueError, match="half-open"):
        DatasetBundle(frame, status_events=pd.DataFrame({"run_id": ["r"], "start": [1.], "stop": [0.],
                                                       "state": [0], "source": ["test"], "scope": ["process"]}))


def test_tep_orientation_selection_labels_and_no_file_reread(tmp_path):
    values = np.arange(6*52, dtype=float).reshape(6, 52)
    np.savetxt(tmp_path / "normal.dat", values.T)
    np.savetxt(tmp_path / "eval.dat", values+1000)
    source = {"sample_period_seconds": 180, "runs": [
        {"run_id": "n", "path": "normal.dat", "source_status": "normal"},
        {"run_id": "e", "path": "eval.dat", "fault_start_zero_based": 2}],
        "variable_groups": [{"group_id": "g", "tag_ids": ["XMEAS_04", "XMEAS_01"]}]}
    from copy import deepcopy
    aliased = deepcopy(source)
    aliased['runs'][1]['path'] = 'normal.dat'
    with pytest.raises(ValueError, match="aliased"):
        load_bundle(aliased, SourceContext(tmp_path))
    bundle = load_bundle(source, SourceContext(tmp_path))
    assert len(bundle.process_values) == 12*52
    assert bundle.tag_alarm_settings.empty
    assert bundle.status_events.state.tolist() == [0, 0, 1]
    (tmp_path / "normal.dat").unlink()
    (tmp_path / "eval.dat").unlink()  # Task Adapter has only Bundle/config, no access to files.
    config = {"group_id": "g", "roles": {"fit": ["n"], "evaluation": ["e"]},
              "alignment": {"maximum_gap_seconds": 180}}
    data = prepare(bundle, config)
    np.testing.assert_array_equal(data.training.fit[0].values, values[:, [3, 0]])
    np.testing.assert_array_equal(data.references[0].labels, [0, 0, 1, 1, 1, 1])
    assert data.references[0].scope == "process"
    config["roles"]["evaluation"] = ["n"]
    with pytest.raises(ValueError, match="overlap"):
        prepare(bundle, config)


def test_alignment_rejects_missing_and_preserves_unknown(tmp_path):
    frame = pd.DataFrame({"run_id": ["r"]*5, "timestamp": [0., 0., 1., 2., 2.],
                          "tag_id": ["x", "y", "x", "x", "y"], "value": [1.]*5, "quality_flag": True})
    from iia_benchmark.data.common.segments import reference_for, select_segments
    bundle = DatasetBundle(frame)
    with pytest.raises(ValueError, match="alignment"):
        select_segments(bundle, ("x", "y"), "r")
    parts = select_segments(bundle, ("y", "x"), "r", missing="break_continuity")
    assert [s.source_indices.tolist() for s in parts] == [[0], [2]]
    assert reference_for(bundle, parts[0]) is None


def test_mat_values_missing_settings_and_continuity_survive_two_adapters(tmp_path):
    from scipy.io import savemat
    from iia_benchmark.data.datasets.power_plant.bundle import load_bundle as load_power
    from iia_benchmark.data.datasets.power_plant.task_adapters.univariate import prepare as prepare_power
    from iia_benchmark.tasks.univariate.contracts import UnivariatePrediction
    from iia_benchmark.tasks.univariate.methods.base import UnivariateMethod
    from iia_benchmark.tasks.base import Detection
    values = np.array([1, 2, -9999, 4, 5, 6, 7, -9999, 9, 10, 11, 12.])
    path = tmp_path / "signal.mat"
    savemat(path, {"A": values})
    original = path.read_bytes()
    bundle = load_power({"path": "signal.mat", "variable": "A", "tag_id": "x", "run_id": "r",
                         "sample_period_seconds": 1, "invalid_below": -1000,
                         "alarm_setting": {"direction": "high", "threshold": 5}}, SourceContext(tmp_path))
    np.testing.assert_array_equal(bundle.process_values.value, values)
    assert bundle.process_values.quality_flag.sum() == 10
    assert path.read_bytes() == original
    path.unlink()
    config = {"tag_id": "x", "direction": "high", "roles": {
        "design": {"run_id": "r", "start_index": 0, "stop_index": 5},
        "evaluation": {"run_id": "r", "start_index": 5, "stop_index": 12}},
        "invalid_policy": "break_continuity", "maximum_gap_seconds": 1,
        "baseline_replay": "declared_instant_threshold_assumption"}
    data = prepare_power(bundle, config)
    assert data.design.alarm.threshold == 5
    assert data.design.alarm.on_delay_seconds is data.design.alarm.deadband is None
    assert [s.source_indices.tolist() for s in data.design.segments] == [[0, 1], [3, 4]]
    assert [s.source_indices.tolist() for s in data.evaluation.segments] == [[5, 6], [8, 9, 10, 11]]
    assert data.references == (None, None)

    class NoStatistics(UnivariateMethod):
        def design(self, view):
            self.threshold = view.alarm.threshold
        def predict(self, view):
            assert not hasattr(view, "references")
            return UnivariatePrediction(tuple(Detection(s.run_id, s.timestamps,
                s.values[:, 0] >= self.threshold) for s in view.segments), {"threshold": self.threshold})

    method = NoStatistics()
    method.design(data.design)
    result = method.predict(data.evaluation)
    assert result.evaluation_references == ()
    for detection, segment in zip(result.detections, data.evaluation.segments, strict=True):
        detection.validate_against(segment)
    config["roles"]["evaluation"]["start_index"] = 4
    with pytest.raises(ValueError, match="overlap"):
        prepare_power(bundle, config)
