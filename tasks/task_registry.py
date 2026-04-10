"""Canonical task ids, legacy aliases, max steps, and dataset pool rules."""

from __future__ import annotations

from typing import Any

# Six canonical tasks (scam-domain names).
CANONICAL_TASK_IDS: tuple[str, ...] = (
    "single_turn_triage",
    "verify_warn_chain",
    "progressive_thread",
    "gray_boundary",
    "otp_kyc_pressure",
    "link_phishing_surface",
)

# Legacy ids from Phase 2 — map to canonical difficulty-based tasks.
TASK_ALIASES: dict[str, str] = {
    "easy": "single_turn_triage",
    "medium": "verify_warn_chain",
    "hard": "progressive_thread",
}

MAX_STEPS_BY_TASK: dict[str, int] = {
    "single_turn_triage": 8,
    "verify_warn_chain": 12,
    "progressive_thread": 20,
    "gray_boundary": 10,
    "otp_kyc_pressure": 12,
    "link_phishing_surface": 10,
}

# Aliases use the same max steps as their canonical target.
for _alias, _canon in TASK_ALIASES.items():
    MAX_STEPS_BY_TASK[_alias] = MAX_STEPS_BY_TASK[_canon]


def resolve_task_id(task_id: str) -> str:
    """Return canonical task id (legacy aliases resolved)."""
    t = task_id.strip()
    return TASK_ALIASES.get(t, t)


# Single canonical grader module (DaddyCoder-style); all tasks dispatch inside tasks.graders.
CANONICAL_GRADER_FILE = "tasks/graders.py"
CANONICAL_GRADER_MODULE = "tasks.graders"


def grader_file_for(_canonical_task_id: str | None = None) -> str:
    """Relative path for manifests; all tasks share tasks/graders.py."""
    return CANONICAL_GRADER_FILE


def grader_module_for(_canonical_task_id: str | None = None) -> str:
    return CANONICAL_GRADER_MODULE


def _joined_text(row: dict[str, Any]) -> str:
    msgs = row.get("messages")
    if msgs:
        return " ".join(str(m) for m in msgs).lower()
    return str(row.get("message", "")).lower()


def scenario_in_task_pool(row: dict[str, Any], canonical_task_id: str) -> bool:
    """Whether a dataset row belongs to the env pool for this task."""
    c = resolve_task_id(canonical_task_id)
    tags = list(row.get("tags") or [])
    diff = str(row.get("difficulty", ""))

    if c == "single_turn_triage":
        return diff == "easy"
    if c == "verify_warn_chain":
        return diff == "medium"
    if c == "progressive_thread":
        return diff == "hard"
    if c == "gray_boundary":
        return "gray_area" in tags
    if c == "otp_kyc_pressure":
        if "kyc" in tags or "otp_language" in tags:
            return True
        t = _joined_text(row)
        return "otp" in t or "kyc" in t
    if c == "link_phishing_surface":
        return bool(row.get("link_present"))
    return False


__all__ = [
    "CANONICAL_GRADER_FILE",
    "CANONICAL_GRADER_MODULE",
    "CANONICAL_TASK_IDS",
    "MAX_STEPS_BY_TASK",
    "TASK_ALIASES",
    "grader_file_for",
    "grader_module_for",
    "resolve_task_id",
    "scenario_in_task_pool",
]
