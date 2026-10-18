"""Pointwise binary definitions shared only when task semantics agree."""
import numpy as np
from iia_benchmark.evaluation.events import detection_delays


def confusion(labels, states):
    labels, states = np.asarray(labels), np.asarray(states)
    if labels.shape != states.shape or labels.ndim != 1 or not np.isin(labels, [-1, 0, 1]).all():
        raise ValueError("aligned -1/0/1 reference and boolean predictions required")
    if states.dtype != np.dtype(bool):
        raise ValueError("states must be boolean")
    return {"tp": int(np.sum((labels == 1) & states)), "fn": int(np.sum((labels == 1) & ~states)),
            "fp": int(np.sum((labels == 0) & states)), "tn": int(np.sum((labels == 0) & ~states)),
            "unknown": int(np.sum(labels == -1))}


def metric(value, definition, reason=None):
    return {"value": value, "status": "available" if value is not None else "unavailable",
            "definition": definition, **({"reason": reason} if value is None else {})}


def point_metrics(counts):
    tp, fn, fp, tn = (counts[k] for k in ("tp", "fn", "fp", "tn"))
    return {
        "F1": metric(2*tp/(2*tp+fp+fn) if tp+fn else None, "2TP/(2TP+FP+FN), known reference points only", "no known abnormal samples"),
        "FAR": metric(fp/(fp+tn) if fp+tn else None, "FP/(FP+TN), normal sample fraction", "no known normal samples"),
        "MAR": metric(fn/(tp+fn) if tp+fn else None, "FN/(TP+FN), abnormal sample fraction", "no known abnormal samples"),
    }


def evaluate_sequences(sequences):
    """Aggregate equal-definition point/delay metrics, keeping segment boundaries.

    sequences yields (timestamps_seconds, reference_labels, boolean_states).
    Reference selection/evidence and task-specific report fields stay in Tasks.
    """
    counts = {key: 0 for key in ("tp", "fn", "fp", "tn", "unknown")}
    delays, missed, censored = [], 0, 0
    for timestamps, labels, states in sequences:
        for key, value in confusion(labels, states).items():
            counts[key] += value
        observed, lost, left = detection_delays(timestamps, labels, states)
        delays.extend(observed)
        missed += lost
        censored += left
    metrics = point_metrics(counts)
    metrics["ADD"] = metric(float(np.mean(delays)) if delays else None,
        "mean first-alarm delay in seconds among detected 0-to-1 events; missed and left-censored events reported separately",
        "no detected event with observed onset")
    return metrics, {"counts": counts, "delay_events": {"detected": len(delays), "missed": missed, "left_censored": censored}}
