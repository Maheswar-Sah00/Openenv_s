#!/usr/bin/env python3
"""Exit 0 if task_graders.json lists enough tasks, ≥3 unique grader entry files, and tasks/graders.py exists."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MIN_TASKS = 3
MIN_UNIQUE_GRADER_FILES = 3


def main() -> int:
    doc = json.loads((ROOT / "task_graders.json").read_text(encoding="utf-8"))
    tasks = doc.get("tasks", [])
    if len(tasks) < MIN_TASKS:
        print(f"task_graders.json: need at least {MIN_TASKS} tasks", file=sys.stderr)
        return 1
    unique_files: set[str] = set()
    for row in tasks:
        rel = row.get("grader_file")
        if not rel or not (ROOT / rel).is_file():
            print(f"Missing grader file: {rel}", file=sys.stderr)
            return 1
        unique_files.add(rel.replace("\\", "/"))
    if len(unique_files) < MIN_UNIQUE_GRADER_FILES:
        print(
            f"task_graders.json: need at least {MIN_UNIQUE_GRADER_FILES} unique grader_file paths "
            f"(got {len(unique_files)})",
            file=sys.stderr,
        )
        return 1
    if not (ROOT / "tasks" / "graders.py").is_file():
        print("Missing canonical tasks/graders.py", file=sys.stderr)
        return 1
    print(
        f"OK: {len(tasks)} tasks, {len(unique_files)} unique grader entry files, tasks/graders.py present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
