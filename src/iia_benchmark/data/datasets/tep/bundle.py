"""Classic Braatz TEP: https://github.com/jkitchin/tennessee-eastman-profbraatz.

Dataset version/checksums are tracked in data/manifest.json. Fault onset is a
source annotation, independent of experiment roles and chosen variable group.
"""
import numpy as np
import pandas as pd

from iia_benchmark.data.contracts import DatasetBundle

FEATURES = tuple([f"XMEAS_{i:02d}" for i in range(1, 42)] + [f"XMV_{i:02d}" for i in range(1, 12)])


def load_bundle(config, context):
    period = float(config["sample_period_seconds"])
    if not np.isfinite(period) or period <= 0:
        raise ValueError("sample period must be finite positive seconds")
    frames, events = [], []
    for run in config["runs"]:
        matrix = np.loadtxt(context.file(run["path"]))
        if matrix.ndim != 2 or matrix.shape == (52, 52):
            raise ValueError("TEP requires an unambiguous sample/52-variable matrix")
        if matrix.shape[1] != 52:
            if matrix.shape[0] != 52:
                raise ValueError("TEP requires 52 variables")
            matrix = matrix.T
        n = len(matrix)
        frames.append(pd.DataFrame({"run_id": run["run_id"], "timestamp": np.repeat(np.arange(n)*period, 52),
                                    "tag_id": np.tile(FEATURES, n), "value": matrix.ravel(),
                                    "quality_flag": np.isfinite(matrix).ravel()}))
        common = {"run_id": run["run_id"], "source": "TEP source run annotation", "scope": run.get("label_scope", "process")}
        if run.get("source_status") == "normal":
            events.append(dict(common, start=0., stop=n*period, state=0))
        elif "fault_start_zero_based" in run:
            onset = run["fault_start_zero_based"]
            if not isinstance(onset, int) or not 0 <= onset < n:
                raise ValueError("fault onset outside source run")
            if onset:
                events.append(dict(common, start=0., stop=onset*period, state=0))
            events.append(dict(common, start=onset*period, stop=n*period, state=1))
    groups = pd.DataFrame([{"group_id": group["group_id"], "tag_id": tag}
                           for group in config.get("variable_groups", []) for tag in group["tag_ids"]])
    return DatasetBundle(pd.concat(frames, ignore_index=True), variable_groups=groups, status_events=pd.DataFrame(events))
