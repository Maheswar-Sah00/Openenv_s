#!/usr/bin/env python3
"""Exit 0 if task_graders.json lists enough tasks and tasks/graders.py exists (single-file layout)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MIN_TASKS = 3


def main() -> int:
    doc = json.loads((ROOT / "task_graders.json").read_text(encoding="utf-8"))
    tasks = doc.get("tasks", [])
    if len(tasks) < MIN_TASKS:
        print(f"task_graders.json: need at least {MIN_TASKS} tasks", file=sys.stderr)
        return 1
    for row in tasks:
        rel = row.get("grader_file")
        if not rel or not (ROOT / rel).is_file():
            print(f"Missing grader file: {rel}", file=sys.stderr)
            return 1
    if not (ROOT / "tasks" / "graders.py").is_file():
        print("Missing canonical tasks/graders.py", file=sys.stderr)
        return 1
    print(f"OK: {len(tasks)} tasks, grader module tasks/graders.py present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
