"""Canonical six-task metadata (ids, steps, grader paths)."""

from __future__ import annotations

from tasks.task_registry import (
    CANONICAL_TASK_IDS,
    MAX_STEPS_BY_TASK,
    grader_file_for,
    grader_module_for,
)

__all__ = [
    "CANONICAL_TASK_IDS",
    "MAX_STEPS_BY_TASK",
    "grader_file_for",
    "grader_module_for",
    "task_spec",
]


def task_spec(task_id: str) -> dict[str, str | int]:
    """Return id, max_steps, grader_file, grader_module for a canonical task id."""
    from tasks.task_registry import resolve_task_id

    c = resolve_task_id(task_id)
    return {
        "id": c,
        "max_steps": MAX_STEPS_BY_TASK[c],
        "grader_file": grader_file_for(c),
        "grader_module": grader_module_for(c),
    }
