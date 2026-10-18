"""Pointwise binary definitions shared only when task semantics agree."""
import numpy as np


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
