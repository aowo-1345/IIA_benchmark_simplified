from iia_benchmark.tasks.base import BaseTask

TASKS: dict[str, type[BaseTask]] = {}


def get_task(kind: str) -> type[BaseTask]:
    try:
        return TASKS[kind]
    except KeyError:
        raise ValueError(f"unsupported task {kind!r}; registered: {sorted(TASKS)}") from None
