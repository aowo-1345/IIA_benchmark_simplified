import numpy as np

from iia_benchmark.evaluation.binary import evaluate_sequences


def evaluate(segments, detections, references):
    sequences, evidence = [], []
    for segment, detection, reference in zip(segments, detections, references, strict=True):
        labels = reference.labels if reference is not None else np.full(len(segment.timestamps), -1)
        sequences.append((segment.timestamps, labels, detection.state))
        evidence.append(None if reference is None else {"source": reference.source, "scope": reference.scope})
    metrics, details = evaluate_sequences(sequences)
    details["references"] = evidence
    return metrics, details
