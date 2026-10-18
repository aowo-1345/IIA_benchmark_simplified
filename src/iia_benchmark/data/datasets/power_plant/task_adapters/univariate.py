import numpy as np
import pandas as pd

from iia_benchmark.data.common.segments import reference_for, select_segments
from iia_benchmark.tasks.base import reject_overlap
from iia_benchmark.tasks.univariate.contracts import (
    AlarmSetting, UnivariateDesignView, UnivariateEvaluationView, UnivariateTaskInput,
)


def prepare(bundle, config):
    tag, direction = config["tag_id"], config["direction"]
    settings = bundle.tag_alarm_settings
    if settings.empty:
        raise ValueError("univariate optimization requires an existing alarm setting")
    selected = settings[(settings.tag_id == tag) & (settings.direction == direction)]
    if len(selected) != 1 or direction not in {"high", "low"}:
        raise ValueError("one unambiguous existing high/low setting required")
    setting = selected.iloc[0]
    def optional(key):
        value = setting.get(key)
        return None if pd.isna(value) else float(value)
    threshold = float(setting.threshold)
    if not np.isfinite(threshold):
        raise ValueError("existing threshold must be finite")
    alarm = AlarmSetting(direction, threshold, str(setting.get("source", "existing alarm table")),
                         optional("on_delay_seconds"), optional("off_delay_seconds"), optional("deadband"))
    minimum = config.get("minimum_segment_samples", 1)
    if not isinstance(minimum, int) or minimum < 1:
        raise ValueError("minimum_segment_samples must be positive integer")
    roles = {}
    for role in ("design", "evaluation"):
        selection = config["roles"][role]
        segments = select_segments(bundle, (tag,), selection["run_id"], start=selection["start_index"],
            stop=selection["stop_index"], missing=config.get("invalid_policy", "reject"),
            maximum_gap_seconds=config.get("maximum_gap_seconds"))
        roles[role] = tuple(s for s in segments if len(s.timestamps) >= minimum)
        if not roles[role]:
            raise ValueError(f"no usable {role} segments")
    reject_overlap(roles.values())
    return UnivariateTaskInput(UnivariateDesignView(roles["design"], alarm,
                               tuple(reference_for(bundle, s) for s in roles["design"])),
                               UnivariateEvaluationView(roles["evaluation"]),
                               tuple(reference_for(bundle, s) for s in roles["evaluation"]),
                               config["baseline_replay"])
