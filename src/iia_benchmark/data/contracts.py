"""Four logical source tables. Timestamps are seconds on each run's time axis.

Use epoch seconds only when the source has absolute time; otherwise retain a
relative sampling origin. A run must use one consistent axis throughout.
Missing optional facts are empty tables, never inferred normal observations.

process_values.quality_flag is boolean: True means a usable measurement.
tag_alarm_settings may omit delay/deadband columns or use null/NaN; neither
means zero. Optional operating_mode/start/stop columns can scope a setting.
variable_groups stores one group_id/tag_id membership per row.
status_events uses half-open [start, stop) seconds; state -1/0/1 means unknown/
normal/abnormal reference, source names its evidence and scope says process,
group or tag (the latter two use group_id/tag_id). Operating-mode-only facts
use state=-1 and operating_mode: a stable mode is not automatically normal.
Optional event_kind='reference' explicitly marks a reference (including unknown)
even when operating_mode is present; event_kind='operating_mode' is only a fact
about mode. Without kind, a state=-1 row with a nonempty operating_mode is mode
only; a state=-1 row without mode is an explicit unknown reference, not absence.
"""
from dataclasses import dataclass, field

import pandas as pd
import numpy as np


@dataclass
class DatasetBundle:
    process_values: pd.DataFrame
    tag_alarm_settings: pd.DataFrame = field(default_factory=pd.DataFrame)
    variable_groups: pd.DataFrame = field(default_factory=pd.DataFrame)
    status_events: pd.DataFrame = field(default_factory=pd.DataFrame)

    def __post_init__(self):
        required = {
            "process_values": {"run_id", "timestamp", "tag_id", "value", "quality_flag"},
            "tag_alarm_settings": {"tag_id", "direction", "threshold"},
            "variable_groups": {"group_id", "tag_id"},
            "status_events": {"run_id", "start", "stop", "state", "source", "scope"},
        }
        for name, columns in required.items():
            table = getattr(self, name)
            if not isinstance(table, pd.DataFrame):
                raise TypeError(f"{name} must be a DataFrame")
            if (name == "process_values" or not table.empty) and not columns <= set(table):
                raise ValueError(f"{name} requires columns {sorted(columns)}")
        self._validate_process_values()
        tags = set(self.process_values.tag_id)
        for table in (self.tag_alarm_settings, self.variable_groups):
            if not table.empty and not set(table.tag_id) <= tags:
                raise ValueError("optional table refers to unknown tag_id")
        self._validate_events()

    def _validate_process_values(self):
        values = self.process_values
        keys = ["run_id", "timestamp", "tag_id"]
        if values[keys].isna().any().any() or values.duplicated(keys).any():
            raise ValueError("process_values requires non-null, unique run/time/tag keys")
        if not np.isfinite(values.timestamp).all() or not values.quality_flag.isin([True, False]).all():
            raise ValueError("timestamps must be finite seconds and quality_flag boolean (True=valid)")
        if not np.isfinite(values.loc[values.quality_flag.astype(bool), "value"]).all():
            raise ValueError("nonfinite values must be marked invalid")

    def _validate_events(self):
        values, events = self.process_values, self.status_events
        if not events.empty:
            if "event_kind" in events and not events.event_kind.dropna().isin(["reference", "operating_mode"]).all():
                raise ValueError("event_kind must be reference, operating_mode or null")
            if not set(events.run_id) <= set(values.run_id) or not events.state.isin([-1, 0, 1]).all():
                raise ValueError("events require known runs and -1/0/1 state")
            if not np.isfinite(events[["start", "stop"]]).all().all() or (events.stop <= events.start).any():
                raise ValueError("events use finite, nonempty half-open [start,stop) seconds")
