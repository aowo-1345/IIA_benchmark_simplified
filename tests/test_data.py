import numpy as np
import pandas as pd
import pytest

from iia_benchmark.data.contracts import DatasetBundle


def test_four_table_facts_reject_ambiguous_keys_and_references():
    frame = pd.DataFrame({"run_id": ["r", "r"], "timestamp": [0., 1.], "tag_id": "x",
                          "value": [1., np.nan], "quality_flag": [True, False]})
    bundle = DatasetBundle(frame)
    assert set(vars(bundle)) == {"process_values", "tag_alarm_settings", "variable_groups", "status_events"}
    assert bundle.status_events.empty  # Absence is unknown, not an inferred normal event.
    with pytest.raises(ValueError, match="unique"):
        DatasetBundle(pd.concat([frame, frame.iloc[:1]], ignore_index=True))
    with pytest.raises(ValueError, match="unknown tag"):
        DatasetBundle(frame, variable_groups=pd.DataFrame({"group_id": ["g"], "tag_id": ["missing"]}))
    with pytest.raises(ValueError, match="half-open"):
        DatasetBundle(frame, status_events=pd.DataFrame({"run_id": ["r"], "start": [1.], "stop": [0.],
                                                       "state": [0], "source": ["test"], "scope": ["process"]}))
