# tasks/graders.py
# Canonical task grading entrypoint (layout aligned with community OpenEnv examples).
# Per-episode scores are strictly in (0, 1); implementation lives in graders/scam_grader.py.

from __future__ import annotations

from pathlib import Path

from graders.scam_grader import (
    MAX_VALID_SCORE,
    MIN_VALID_SCORE,
    finalize_episode_score,
    grade_episode as _grade_episode_impl,
    load_scenario_by_id,
)

# Re-export for inference / scripts / static discovery
grade_episode = _grade_episode_impl

__all__ = [
    "TASK_IDS_WITH_GRADERS",
    "grade_action",
    "grade_episode",
    "finalize_episode_score",
    "load_scenario_by_id",
    "MIN_VALID_SCORE",
    "MAX_VALID_SCORE",
    "_grade_easy",
    "_grade_medium",
    "_grade_hard",
]

TASK_IDS_WITH_GRADERS: tuple[str, ...] = ("easy", "medium", "hard")


def grade_action(
    task_id: str,
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    """Score a completed episode for ``task_id`` (OpenEnv-style name; same as ``grade_episode``)."""
    return _grade_episode_impl(task_id, action_trace, scenario_id, data_path)


def _grade_easy(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return _grade_episode_impl("easy", action_trace, scenario_id, data_path)


def _grade_medium(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return _grade_episode_impl("medium", action_trace, scenario_id, data_path)


def _grade_hard(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return _grade_episode_impl("hard", action_trace, scenario_id, data_path)
