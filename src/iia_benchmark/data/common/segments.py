"""Bundle facts to continuous numeric segments; no source files or learning."""
import numpy as np
import pandas as pd

from iia_benchmark.tasks.base import Reference, SignalSegment, reject_overlap


def select_segments(bundle, tags, run_id, *, start=0, stop=None, missing="reject", maximum_gap_seconds=None):
    matrix, quality, timeline = _aligned_run(bundle, tags, run_id)
    stop = len(timeline) if stop is None else stop
    if not isinstance(start, int) or not isinstance(stop, int) or not 0 <= start < stop <= len(timeline):
        raise ValueError("invalid half-open sample-index selection")
    values = matrix.to_numpy(float)[start:stop]
    times = timeline[start:stop].astype(float)
    valid = quality.eq(True).to_numpy(bool)[start:stop].all(axis=1) & np.isfinite(values).all(axis=1)
    if missing not in {"reject", "break_continuity"}:
        raise ValueError("missing policy must be reject or break_continuity")
    if missing == "reject" and not valid.all():
        raise ValueError("missing or invalid samples prevent exact alignment")
    gaps = np.zeros(len(times), bool)
    if maximum_gap_seconds is not None:
        if maximum_gap_seconds <= 0:
            raise ValueError("maximum_gap_seconds must be positive")
        gaps[1:] = np.diff(times) > maximum_gap_seconds * (1 + 1e-9)
    edges = np.flatnonzero(np.r_[True, valid[1:] != valid[:-1]] | gaps)
    ends = np.r_[edges[1:], len(times)]
    return tuple(SignalSegment(run_id, times[a:b].copy(), values[a:b].copy(),
                               np.arange(start+a, start+b), tuple(tags))
                 for a, b in zip(edges, ends, strict=True) if valid[a])


def reference_for(bundle, segment, group_id=None):
    labels = np.full(len(segment.timestamps), -1, dtype=np.int8)
    sources, scopes = set(), set()
    events = bundle.status_events
    if events.empty:
        return None
    for event in events[events.run_id == segment.run_id].itertuples():
        if not _event_applies(event, segment, group_id):
            continue
        mask = (segment.timestamps >= event.start) & (segment.timestamps < event.stop)
        if not mask.any() or not _is_reference_event(event):
            continue
        if event.state != -1:
            if np.any((labels[mask] != -1) & (labels[mask] != event.state)):
                raise ValueError("conflicting reference intervals")
            labels[mask] = event.state
        sources.add(event.source)
        scopes.add(event.scope)
    return Reference(labels, "; ".join(sorted(sources)), "; ".join(sorted(scopes))) if sources else None


def _is_reference_event(event):
    kind = getattr(event, "event_kind", None)
    if pd.notna(kind):
        return kind == "reference"
    if event.state != -1:
        return True
    mode = getattr(event, "operating_mode", None)
    return pd.isna(mode) or mode == ""



def _aligned_run(bundle, tags, run_id):
    run = bundle.process_values.loc[bundle.process_values.run_id == run_id]
    if run.empty or not set(tags) <= set(run.tag_id):
        raise ValueError(f"unknown run/tags: {run_id}, {tags}")
    timeline = np.sort(run.timestamp.unique())
    selected = run[run.tag_id.isin(tags)]
    matrix = selected.pivot(index="timestamp", columns="tag_id", values="value").reindex(index=timeline, columns=tags)
    quality = selected.pivot(index="timestamp", columns="tag_id", values="quality_flag").reindex(index=timeline, columns=tags)
    return matrix, quality, timeline


def _event_applies(event, segment, group_id):
    if event.scope == "process":
        return True
    if event.scope == "group":
        return getattr(event, "group_id", None) == group_id
    if event.scope == "tag":
        return len(segment.feature_names) == 1 and getattr(event, "tag_id", None) == segment.feature_names[0]
    return False
