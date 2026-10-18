from iia_benchmark.tasks.base import BaseTask
from iia_benchmark.tasks.multivariate.task import MultivariateTask

TASKS: dict[str, type[BaseTask]] = {"multivariate_detection": MultivariateTask}


def get_task(kind: str) -> type[BaseTask]:
    try:
        return TASKS[kind]
    except KeyError:
        raise ValueError(f"unsupported task {kind!r}; registered: {sorted(TASKS)}") from None
