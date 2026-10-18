"""Bundle facts to continuous numeric segments; no source files or learning."""
import numpy as np

from iia_benchmark.tasks.base import Reference, SignalSegment


def select_segments(bundle, tags, run_id, *, start=0, stop=None, missing="reject", maximum_gap_seconds=None):
    frame = bundle.process_values
    run = frame[frame.run_id == run_id]
    if run.empty or not set(tags) <= set(run.tag_id):
        raise ValueError(f"unknown run/tags: {run_id}, {tags}")
    timeline = np.sort(run.timestamp.unique())
    stop = len(timeline) if stop is None else stop
    if not isinstance(start, int) or not isinstance(stop, int) or not 0 <= start < stop <= len(timeline):
        raise ValueError("invalid half-open sample-index selection")
    selected = run[run.tag_id.isin(tags)]
    matrix = selected.pivot(index="timestamp", columns="tag_id", values="value").reindex(index=timeline, columns=tags)
    quality = selected.pivot(index="timestamp", columns="tag_id", values="quality_flag").reindex(index=timeline, columns=tags)
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
        if event.scope == "group" and getattr(event, "group_id", None) != group_id:
            continue
        if event.scope == "tag" and (len(segment.feature_names) != 1 or getattr(event, "tag_id", None) != segment.feature_names[0]):
            continue
        if event.scope not in {"process", "group", "tag"}:
            continue
        mask = (segment.timestamps >= event.start) & (segment.timestamps < event.stop)
        if event.state == -1 or not mask.any():
            continue
        if np.any((labels[mask] != -1) & (labels[mask] != event.state)):
            raise ValueError("conflicting reference intervals")
        labels[mask] = event.state
        sources.add(event.source)
        scopes.add(event.scope)
    return Reference(labels, "; ".join(sorted(sources)), "; ".join(sorted(scopes))) if sources else None


def reject_overlap(roles):
    used = {}
    for segments in roles:
        for segment in segments:
            start, stop = int(segment.source_indices[0]), int(segment.source_indices[-1]) + 1
            intervals = used.setdefault(segment.run_id, [])
            if any(start < b and a < stop for a, b in intervals):
                raise ValueError("roles/segments overlap in original run samples")
            intervals.append((start, stop))
