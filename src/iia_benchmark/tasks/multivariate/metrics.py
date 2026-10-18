import numpy as np

from iia_benchmark.evaluation.binary import confusion, metric, point_metrics
from iia_benchmark.evaluation.events import detection_delays


def evaluate(segments, detections, references):
    counts = {key: 0 for key in ("tp", "fn", "fp", "tn", "unknown")}
    delays, missed, censored, evidence = [], 0, 0, []
    for segment, detection, reference in zip(segments, detections, references, strict=True):
        labels = reference.labels if reference is not None else np.full(len(segment.timestamps), -1)
        for key, value in confusion(labels, detection.state).items():
            counts[key] += value
        observed, lost, left = detection_delays(segment.timestamps, labels, detection.state)
        delays.extend(observed)
        missed += lost
        censored += left
        evidence.append(None if reference is None else {"source": reference.source, "scope": reference.scope})
    metrics = point_metrics(counts)
    metrics["ADD"] = metric(float(np.mean(delays)) if delays else None,
        "mean first-alarm delay in seconds among detected 0-to-1 events; missed and left-censored events reported separately",
        "no detected event with observed onset")
    return metrics, {"counts": counts, "delay_events": {"detected": len(delays), "missed": missed, "left_censored": censored},
                     "references": evidence}
