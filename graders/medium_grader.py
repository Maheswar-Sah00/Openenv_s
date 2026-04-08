"""Grader for the **medium** task — one file per task for Phase 2 static checks."""

from __future__ import annotations

from pathlib import Path

from graders.scam_grader import grade_episode as _grade_episode

TASK_ID = "medium"


def grade(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    """Return grader score in (0, 1) open for this episode."""
    return _grade_episode(TASK_ID, action_trace, scenario_id, data_path)


def grade_episode(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    """Alias matching shared API; same as ``grade``."""
    return grade(action_trace, scenario_id, data_path)
