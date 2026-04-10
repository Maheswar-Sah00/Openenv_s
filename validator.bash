#!/usr/bin/env bash
# Local preflight: task grader checks; optional openenv validate when CLI is installed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT"
python -m unittest tests.test_task_graders -v
python scripts/verify_task_graders.py
if command -v openenv >/dev/null 2>&1; then
  openenv validate || echo "openenv validate: skipped or failed (install openenv-core[cli] to enforce)"
fi
echo "validator.bash: OK"
