"""Complete threshold/delay/deadband rule, book Chapter 2.

Reference doi:10.1007/978-981-97-6516-4. Default onset_shift high alarms enter
at H+d (inclusive) and recover below H (strict). Explicit recovery_shift enters
at H and recovers below H-d; low alarms mirror the chosen convention.
Each delay is elapsed seconds from first consecutive qualifying observation.
Zero means immediate. On a regular period dt, book n points = (n-1)*dt seconds.
No interpolation: segment boundaries always reset state and pending timers.
"""
import numpy as np

from iia_benchmark.tasks.base import Detection
from iia_benchmark.tasks.univariate.contracts import UnivariatePrediction
from iia_benchmark.tasks.univariate.methods.base import UnivariateMethod


def _qualified_events(mask, timestamps, delay):
    edges = np.diff(np.r_[False, mask, False].astype(np.int8))
    starts, stops = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    ready = np.searchsorted(timestamps, timestamps[starts] + delay, side="left")
    return ready[ready < stops]


def apply_rule(segment, parameters):
    values, times = segment.values[:, 0], segment.timestamps
    threshold, band = parameters["threshold"], parameters["deadband"]
    shift_on = band if parameters["deadband_mode"] == "onset_shift" else 0.
    shift_off = band - shift_on
    if parameters["direction"] == "high":
        on, off = values >= threshold + shift_on, values < threshold - shift_off
    else:
        on, off = values <= threshold - shift_on, values > threshold + shift_off
    on_events = _qualified_events(on, times, parameters["on_delay_seconds"])
    off_events = _qualified_events(off, times, parameters["off_delay_seconds"])
    positions = np.r_[on_events, off_events]
    targets = np.r_[np.ones(len(on_events), bool), np.zeros(len(off_events), bool)]
    order = np.argsort(positions)
    states = np.repeat(np.r_[False, targets[order]], np.diff(np.r_[0, positions[order], len(values)]))
    return Detection(segment.run_id, times.copy(), states)


class ThresholdRuleMethod(UnivariateMethod):
    def __init__(self, *, threshold=None, on_delay_seconds=0., off_delay_seconds=0., deadband=0., deadband_mode="onset_shift"):
        if deadband_mode not in {"onset_shift", "recovery_shift"}:
            raise ValueError("deadband_mode must be onset_shift or recovery_shift")
        if threshold is not None and not np.isfinite(threshold):
            raise ValueError("threshold must be finite")
        if not np.isfinite([on_delay_seconds, off_delay_seconds, deadband]).all() or min(on_delay_seconds, off_delay_seconds, deadband) < 0:
            raise ValueError("delay seconds and deadband must be finite nonnegative")
        self.config = dict(threshold=threshold, on_delay_seconds=on_delay_seconds, off_delay_seconds=off_delay_seconds,
                           deadband=deadband, deadband_mode=deadband_mode)
        self.parameters = None

    def design(self, data):
        if data.alarm.direction not in {"high", "low"}:
            raise ValueError("unsupported alarm direction")
        self.parameters = dict(self.config, direction=data.alarm.direction)
        if self.parameters["threshold"] is None:
            self.parameters["threshold"] = data.alarm.threshold

    def predict(self, data):
        if self.parameters is None:
            raise ValueError("design must precede predict")
        return UnivariatePrediction(tuple(apply_rule(s, self.parameters) for s in data.segments), dict(self.parameters))
