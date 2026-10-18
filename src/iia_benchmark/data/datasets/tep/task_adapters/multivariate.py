from iia_benchmark.data.common.segments import reference_for, reject_overlap, select_segments
from iia_benchmark.tasks.multivariate.contracts import (
    MultivariateEvaluationView, MultivariateTaskInput, MultivariateTrainingView,
)


def prepare(bundle, config):
    group = config["group_id"]
    groups = bundle.variable_groups
    if groups.empty or group not in set(groups.group_id):
        raise ValueError(f"unknown variable group {group}")
    tags = tuple(groups.loc[groups.group_id == group, "tag_id"])
    if len(set(tags)) != len(tags):
        raise ValueError("duplicate group membership")
    alignment = config.get("alignment", {})
    if alignment.get("mode", "exact_timestamp") != "exact_timestamp":
        raise ValueError("only exact_timestamp alignment is supported")
    roles = {}
    for role in ("fit", "calibration", "evaluation"):
        roles[role] = tuple(segment for run in config["roles"].get(role, [])
                            for segment in select_segments(bundle, tags, run,
                                missing=alignment.get("missing", "reject"),
                                maximum_gap_seconds=alignment.get("maximum_gap_seconds")))
    if not roles["fit"] or not roles["evaluation"]:
        raise ValueError("fit and evaluation require valid samples")
    reject_overlap(roles.values())
    bases = []
    for segment in roles["fit"] + roles["calibration"]:
        ref = reference_for(bundle, segment, group)
        if ref is None or not (ref.labels == 0).all():
            raise ValueError("normal fitting/calibration requires explicit source normal evidence")
        bases.append(ref.source)
    return MultivariateTaskInput(MultivariateTrainingView(roles["fit"], roles["calibration"]),
                                 MultivariateEvaluationView(roles["evaluation"]),
                                 tuple(reference_for(bundle, s, group) for s in roles["evaluation"]),
                                 "; ".join(sorted(set(bases))), group)
