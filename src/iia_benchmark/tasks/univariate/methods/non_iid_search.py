"""Book Ch.2.1.3 reference construction + Ch.2.2 duration-tail design.

Reference: Wang/Hu/Chen, doi:10.1007/978-981-97-6516-4, printed pp60–61,
69–85. This bounded grid/deadband combination is a local method transfer,
not reproduction of Example 3 or a guarantee of the Task's pointwise FAR/MAR.
Complete excursion/gap counts use Beta(1,1) posterior means. Censored runs at
reference/continuity boundaries are excluded, and segments are never joined.
"""
from itertools import product

import numpy as np
from scipy.stats import beta as beta_distribution, rankdata, t as student_t

from iia_benchmark.evaluation.events import intervals
from iia_benchmark.tasks.base import Reference
from iia_benchmark.tasks.univariate.contracts import UnivariatePrediction
from iia_benchmark.tasks.univariate.methods.base import UnivariateMethod
from iia_benchmark.tasks.univariate.methods.threshold_rule import apply_rule


def _partitions(values, minimum, alpha):
    pending, result = [(0, len(values))], []
    while pending:
        start, stop = pending.pop()
        n = stop-start
        if n >= 2*minimum:
            ranks = rankdata(values[start:stop], method="average")
            u = 2*np.cumsum(ranks)[:-1] - np.arange(1, n)*(n+1)
            split = int(np.argmax(np.abs(u)))+1
            p = min(1., float(2*np.exp(-6*float(u[split-1])**2/(n**3+n**2))))
            if p < alpha and minimum <= split <= n-minimum:
                pending.extend(((start, start+split), (start+split, stop)))
                continue
        result.append((start, stop))
    return sorted(result)


def statistical_reference(segment, threshold, direction, minimum, alpha, beta):
    values = segment.values[:, 0]
    labels, records = np.full(len(values), -1, dtype=np.int8), []
    for start, stop in _partitions(values, minimum, alpha):
        chunk, state, statistic = values[start:stop], -1, None
        n, mean = len(chunk), float(np.mean(chunk))
        if n >= minimum:
            deviation = float(np.std(chunk, ddof=1))
            difference = (mean-threshold) * (1 if direction == "high" else -1)
            if deviation == 0:
                state = 1 if difference > 0 else 0 if difference < 0 else -1
            else:
                # Printed book p61 uses sqrt(n-1) with the sample SD (ddof=1).
                statistic = float(difference/(deviation/np.sqrt(n-1)))
                critical = float(student_t.ppf(1-beta, n-1))
                state = 1 if statistic > critical else 0 if statistic < -critical else -1
        labels[start:stop] = state
        records.append({"run_id": segment.run_id, "start_source_index": int(segment.source_indices[start]),
            "stop_source_index": int(segment.source_indices[stop-1])+1, "samples": n, "mean": mean,
            "signed_t_statistic": statistic, "state": state})
    return Reference(labels, f"statistical_proxy:pettitt_ttest; existing_threshold={threshold}", "tag"), records


def _complete_lengths(chunks, threshold, above):
    lengths = []
    for values in chunks:
        mask = values >= threshold if above else values < threshold
        lengths.extend(stop-start for start, stop in intervals(mask) if start > 0 and stop < len(mask))
    return np.asarray(lengths, dtype=int)


class NonIIDSearchMethod(UnivariateMethod):
    def __init__(self, *, thresholds, delay_samples, deadbands=(0.,), minimum_segment_samples=3600,
                 pettitt_alpha=.05, ttest_beta=.05, target_normal_event_tail=.05,
                 target_abnormal_gap_tail=.05, normal_weight=.5, confidence=.95):
        self.thresholds, self.delays, self.deadbands = sorted(set(thresholds)), sorted(set(delay_samples)), sorted(set(deadbands))
        if not all((self.thresholds, self.delays, self.deadbands)) or not np.isfinite(self.thresholds+self.deadbands).all():
            raise ValueError("finite nonempty candidate grids required")
        if any(not isinstance(n, int) or n < 1 for n in self.delays) or min(self.deadbands) < 0:
            raise ValueError("delays must be positive integer sample counts and deadbands nonnegative")
        if not isinstance(minimum_segment_samples, int) or minimum_segment_samples < 2:
            raise ValueError("minimum_segment_samples must be at least two")
        if not all([0 < pettitt_alpha < 1, 0 < ttest_beta < 1, 0 < confidence < 1]):
            raise ValueError("test probabilities/confidence must be in (0,1)")
        if not all([0 <= target_normal_event_tail <= 1, 0 <= target_abnormal_gap_tail <= 1, 0 <= normal_weight <= 1]):
            raise ValueError("targets/weight must be in [0,1]")
        self.minimum, self.alpha, self.beta = minimum_segment_samples, pettitt_alpha, ttest_beta
        self.targets, self.weight, self.confidence = (target_normal_event_tail, target_abnormal_gap_tail), normal_weight, confidence
        self.parameters = None

    def _reference(self, segment):
        return statistical_reference(segment, self.reference_threshold, self.direction, self.minimum, self.alpha, self.beta)

    def design(self, data):
        self.parameters = None
        self.reference_threshold, self.direction = data.alarm.threshold, data.alarm.direction
        differences = np.concatenate([np.diff(s.timestamps) for s in data.segments])
        if not len(differences) or not np.allclose(differences, differences[0]):
            raise ValueError("duration-sample design requires one regular sampling period")
        period = float(differences[0])
        chunks, self.design_records, self.design_sources = {0: [], 1: []}, [], []
        for segment, external in zip(data.segments, data.references, strict=True):
            reference, records = (external, []) if external is not None else self._reference(segment)
            self.design_sources.append({"source": reference.source, "scope": reference.scope})
            self.design_records.extend(records)
            for state in (0, 1):
                chunks[state].extend(segment.values[a:b, 0] for a, b in intervals(reference.labels == state))
        if not chunks[0] or not chunks[1]:
            raise ValueError("design needs both normal and abnormal references; cannot fabricate missing class")
        self.search = self._search(chunks)
        selected = self.search["candidates"][0]
        self.parameters = dict(threshold=selected["threshold"], direction=self.direction,
            on_delay_seconds=(selected["delay_samples"]-1)*period, off_delay_seconds=(selected["delay_samples"]-1)*period,
            deadband=selected["deadband"], deadband_mode="onset_shift")

    def _search(self, chunks):
        candidates = []
        # Mirror low alarms into a high-alarm coordinate without joining chunks.
        sign = 1 if self.direction == "high" else -1
        normal, abnormal = ([sign*x for x in chunks[state]] for state in (0, 1))
        for threshold, band in product(self.thresholds, self.deadbands):
            high = _complete_lengths(normal, sign*threshold+band, True)
            low = _complete_lengths(abnormal, sign*threshold, False)
            if not len(high) or not len(low):
                continue
            for delay in self.delays:
                successes = [int(np.sum(lengths >= delay)) for lengths in (high, low)]
                trials = [len(high), len(low)]
                tails = [(s+1)/(n+2) for s, n in zip(successes, trials)]
                loss = self.weight*abs(tails[0]-self.targets[0])+(1-self.weight)*abs(tails[1]-self.targets[1])
                candidates.append(dict(threshold=float(threshold), delay_samples=int(delay), deadband=float(band),
                                       loss=float(loss), posterior_means=tails, successes=successes, trials=trials))
        if not candidates:
            raise ValueError("no candidate has both complete normal excursions and abnormal gaps")
        candidates.sort(key=lambda c: (c["loss"], abs(c["threshold"]-self.reference_threshold), c["delay_samples"], c["deadband"], c["threshold"]))
        selected = candidates[0]
        probability = (1-self.confidence)/2
        credible = [beta_distribution.ppf([probability, 1-probability], s+1, n-s+1).tolist()
                    for s, n in zip(selected["successes"], selected["trials"])]
        return {"candidates": candidates, "evaluated": len(candidates), "confidence": self.confidence,
                "selected_tail_intervals": credible,
                "objective": "weighted absolute distance of complete normal excursion/abnormal gap tail posterior means from targets; not pointwise Task FAR/MAR"}

    def predict(self, data):
        if self.parameters is None:
            raise ValueError("design must precede predict")
        references, records = [], []
        for segment in data.segments:
            reference, parts = self._reference(segment)
            references.append(reference)
            records.extend(parts)
        details = {"design_segments": self.design_records, "design_reference_sources": self.design_sources,
            "evaluation_segments": records, "design_search": self.search,
            "reference_threshold": self.reference_threshold, "pettitt_alpha": self.alpha, "ttest_beta": self.beta,
            "minimum_segment_samples": self.minimum,
            "basis": "method-generated statistical reference, not independently confirmed incidents",
            "assumptions": "distinct state means and engineering interpretation relative to original threshold; t-test proxy may be affected by autocorrelation; no evaluation data used to select parameters"}
        return UnivariatePrediction(tuple(apply_rule(s, self.parameters) for s in data.segments),
                                    dict(self.parameters), tuple(references), details)
