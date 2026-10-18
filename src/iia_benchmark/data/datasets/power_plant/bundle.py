"""Delay timer dataset Example 3, doi:10.1016/j.jprocont.2022.01.002.

The paper's Example 3 uses fixed-threshold delay design. Our later statistical
joint search is a method transfer, not that paper's original experiment.
"""
import numpy as np
import pandas as pd
from scipy.io import loadmat

from iia_benchmark.data.contracts import DatasetBundle


def load_bundle(config, context):
    payload = loadmat(context.file(config["path"]), squeeze_me=True)
    values = np.asarray(payload[config["variable"]], dtype=float).squeeze()
    if values.ndim != 1 or not len(values):
        raise ValueError("MAT variable must be a nonempty one-dimensional signal")
    period = float(config["sample_period_seconds"])
    if not np.isfinite(period) or period <= 0:
        raise ValueError("sample period must be finite positive seconds")
    valid = np.isfinite(values)
    if "invalid_below" in config:
        valid &= values >= config["invalid_below"]
    tag = config["tag_id"]
    frame = pd.DataFrame({"run_id": config["run_id"], "timestamp": np.arange(len(values))*period,
                          "tag_id": tag, "value": values, "quality_flag": valid})
    setting = dict(config["alarm_setting"], tag_id=tag, source="dataset configuration: existing alarm")
    return DatasetBundle(frame, tag_alarm_settings=pd.DataFrame([setting]))
