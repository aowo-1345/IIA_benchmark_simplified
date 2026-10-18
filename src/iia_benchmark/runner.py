"""One public execution path, independent of source layout and learning algorithm."""
import argparse
from pathlib import Path
import subprocess
import sys
from importlib.metadata import version

from iia_benchmark.config.loader import load_experiment
from iia_benchmark.data.contracts import DatasetBundle
from iia_benchmark.data.registry import SourceContext, get_bundle_adapter, get_task_adapter
from iia_benchmark.results.writer import create_run, write_json, write_result
from iia_benchmark.tasks.factory import get_task


def run_experiment(path, output_root=None) -> Path:
    plan = load_experiment(path)
    configs = plan.snapshot
    task = get_task(configs["task"]["kind"])(configs["task"]["parameters"])
    model = configs["model"]
    method = task.create_method(model["method"], model["parameters"])
    load = get_bundle_adapter(configs["dataset"]["adapter"])
    adapter = get_task_adapter(configs["task_adapter"]["adapter"])
    if adapter.task_kind != configs["task"]["kind"] or adapter.input_type is not task.input_type:
        raise ValueError("registered Task Adapter is incompatible with selected Task")
    target = Path(output_root).resolve() if output_root is not None else plan.root / "experiments/runs"
    directory, started = create_run(target, configs["experiment"]["name"])
    sources = SourceContext(plan.root)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=plan.root, capture_output=True, text=True)
    manifest = {"started": started, "output": str(directory), "config_paths": plan.config_paths,
                "git_commit": revision.stdout.strip() if revision.returncode == 0 else None,
                "git_dirty": bool(subprocess.run(["git", "status", "--porcelain"], cwd=plan.root,
                                                capture_output=True, text=True).stdout.strip()),
                "versions": {"python": sys.version.split()[0], **{name: version(name) for name in ("numpy", "pandas", "scipy")}},
                "status": "running", "sources": sources.sources}
    write_json(directory / "config.snapshot.json", configs)
    try:
        bundle = load(configs["dataset"]["adapter_config"], sources)
        if not isinstance(bundle, DatasetBundle):
            raise TypeError("source Adapter must return DatasetBundle")
        data = adapter.prepare(bundle, configs["task_adapter"]["adapter_config"])
        if not isinstance(data, task.input_type):
            raise TypeError("Task Adapter returned incompatible input")
        result = task.run(data, method)
        write_result(directory, result)
        manifest["status"] = "completed"
    except Exception as exc:
        manifest.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        write_json(directory / "manifest.json", manifest)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    print(run_experiment(args.experiment, args.output_root))


if __name__ == "__main__":
    main()
