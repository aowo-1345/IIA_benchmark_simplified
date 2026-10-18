from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def create_run(root: Path, name: str) -> tuple[Path, str]:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    directory = root / now.strftime("%Y-%m-%d") / name / (now.strftime("%H%M%S") + "-" + uuid4().hex[:10])
    directory.mkdir(parents=True, exist_ok=False)
    return directory, now.isoformat()


def write_result(directory, result):
    result.predictions.to_csv(directory / "predictions.csv", index=False)
    write_json(directory / "metrics.json", result.metrics)
    write_json(directory / "details.json", result.details)
