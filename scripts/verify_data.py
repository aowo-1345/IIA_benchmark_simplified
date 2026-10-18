"""核对 data/manifest.json 登记的本地副本；只使用 Python 标准库。"""

import hashlib
import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "data/manifest.json").read_text(encoding="utf-8"))
    failures = 0
    total_files = 0
    total_bytes = 0
    for dataset in manifest["datasets"]:
        dataset_failures = 0
        for record in dataset["files"]:
            path = root / record["path"]
            if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root):
                reason = "不能使用软链接"
            elif not path.is_file():
                reason = "文件缺失"
            elif path.stat().st_size != record["bytes"]:
                reason = "文件大小不符"
            else:
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                reason = "SHA-256 不符" if digest.hexdigest() != record["sha256"] else ""
            if reason:
                print(f"FAIL {record['path']}: {reason}")
                dataset_failures += 1
            total_files += 1
            total_bytes += record["bytes"]
        failures += dataset_failures
        state = "FAIL" if dataset_failures else "OK"
        print(f"{state} {dataset['id']}: {len(dataset['files'])} 个文件")
    print(f"清单共 {total_files} 个文件，{total_bytes:,} 字节；失败 {failures} 项")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
