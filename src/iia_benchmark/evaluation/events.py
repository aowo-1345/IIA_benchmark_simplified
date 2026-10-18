import numpy as np


def intervals(mask):
    """Half-open true runs; boundaries are never joined across calls."""
    changes = np.diff(np.r_[False, np.asarray(mask, bool), False].astype(np.int8))
    return tuple(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1), strict=True))


def detection_delays(timestamps, labels, states):
    """Observed 0→1 reference onsets, detected within that same abnormal event.

    Segment-start/unknown→abnormal intervals are left-censored and excluded.
    Missed events count separately: they do not contribute fictitious zero delay.
    An alarm already active at the onset counts as zero delay.
    """
    delays, missed, censored = [], 0, 0
    for start, stop in intervals(labels == 1):
        if start == 0 or labels[start-1] != 0:
            censored += 1
            continue
        hits = np.flatnonzero(states[start:stop])
        if len(hits):
            delays.append(float(timestamps[start+hits[0]] - timestamps[start]))
        else:
            missed += 1
    return delays, missed, censored
