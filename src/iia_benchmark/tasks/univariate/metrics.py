import numpy as np

from iia_benchmark.evaluation.binary import evaluate_sequences, metric
from iia_benchmark.evaluation.events import intervals


def _event_count(states, merge_gap):
    runs = intervals(states)
    if not runs:
        return 0
    return int(1 + sum(start - previous_stop > merge_gap for (_, previous_stop), (start, _) in zip(runs, runs[1:])))


def evaluate(segments, detections, baseline, references, merge_gap):
    sequences, baseline_sequences, evidence = [], [], []
    for segment, detection, base, reference in zip(segments, detections, baseline, references, strict=True):
        labels = reference.labels if reference is not None else np.full(len(segment.timestamps), -1)
        sequences.append((segment.timestamps, labels, detection.state))
        baseline_sequences.append((segment.timestamps, labels, base.state))
        evidence.append(None if reference is None else {"source": reference.source, "scope": reference.scope})
    metrics, details = evaluate_sequences(sequences)
    baseline_metrics, baseline_details = evaluate_sequences(baseline_sequences)
    before = sum(_event_count(d.state, merge_gap) for d in baseline)
    after = sum(_event_count(d.state, merge_gap) for d in detections)
    metrics["alarm_compression_rate"] = metric(1-after/before if before else None,
        "1 - candidate alarm-onset events / baseline alarm-onset events on identical segments",
        "no baseline alarm events")
    details.update(references=evidence, baseline_metrics=baseline_metrics, baseline_evaluation=baseline_details,
                   alarm_events={"baseline": before, "candidate": after, "merge_gap_samples": merge_gap})
    return metrics, details
