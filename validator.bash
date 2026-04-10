#!/usr/bin/env bash
#
# OpenEnv submission validator: delegates Steps 1–3 to scripts/validate-submission.sh (HF ping,
# docker build, openenv validate), then runs Step 4 — local grader registry checks.
#
# Usage (from repo root):
#   ./validator.bash https://<user>-<space>.hf.space
#   ./validator.bash   # skips Steps 1–3; runs Step 4 only (no ping URL)
#

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ -t 1 ]; then
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BOLD='\033[1m'
  NC='\033[0m'
else
  GREEN='' YELLOW='' BOLD='' NC=''
fi

if [ "${1:-}" != "" ]; then
  bash "$ROOT/scripts/validate-submission.sh" "$@"
else
  printf "%b\n" "${YELLOW}[validator] No ping URL — skipping Steps 1–3 (HF / Docker / openenv).${NC}"
  printf "  Full run: ${BOLD}./validator.bash https://<user>-<space>.hf.space${NC}\n"
  printf "\n"
fi

printf "${BOLD}Step 4/4: Task grader checks (local)${NC}\n"
export PYTHONPATH="${PYTHONPATH:-}:${ROOT}"
python scripts/verify_task_graders.py
python -m unittest tests.test_task_graders -q
python -c "from tasks.graders import GRADERS; print('GRADERS registry:', len(GRADERS), 'tasks —', sorted(GRADERS.keys()))"

printf "\n%b\n" "${GREEN}PASSED${NC} -- Step 4: task grader checks complete"
printf "${GREEN}All validator steps finished.${NC}\n"
