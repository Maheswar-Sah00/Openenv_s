# tasks/graders.py
# Episode-level reward functions for each task. All reported scores are strictly in (0.0, 1.0).
# Layout mirrors community OpenEnv examples (sectioned task-specific helpers + dispatch).

from __future__ import annotations

from pathlib import Path
from typing import Any

from tasks.database import load_scenario_by_id
from tasks.task_registry import resolve_task_id

# Hackathon / Phase 2: scores strictly inside (0, 1) — not 0.0, not 1.0.
MIN_VALID_SCORE = 0.01
MAX_VALID_SCORE = 0.99


def _safe_score(value: float) -> float:
    """Clamp any float to strictly within (0, 1)."""
    return round(min(max(float(value), MIN_VALID_SCORE), MAX_VALID_SCORE), 2)


def finalize_episode_score(value: float | None) -> float:
    """For stdout [END] when grading skipped (errors) or final score line."""
    if value is None:
        return _safe_score(0.0)
    return _safe_score(value)


# ---------------------------------------------------------------------------
# Core rubrics (difficulty-shaped): single-turn, verify chain, progressive thread
# ---------------------------------------------------------------------------


def _grade_single_turn_triage(is_scam: bool, trace: list[str], gray: bool = False) -> float:
    """Obvious one-shot scam vs legitimate (legacy: easy)."""
    if is_scam:
        if "ignore" in trace:
            return 0.15 if gray else 0.0
        if "flag_scam" in trace or "escalate_to_bank" in trace:
            if gray and "verify_sender" not in trace:
                return 0.82
            return 1.0
        if "block_sender" in trace:
            return 0.85 if not gray else 0.78
        if "warn_user" in trace:
            return 0.35
        return 0.0
    if "flag_scam" in trace or "block_sender" in trace:
        return 0.25 if gray else 0.0
    if "ignore" in trace:
        return 0.92 if gray else 1.0
    if "verify_sender" in trace and "warn_user" not in trace and "flag_scam" not in trace:
        return 0.75 if gray else 0.7
    return 0.55 if gray else 0.5


def _grade_verify_warn_chain(is_scam: bool, trace: list[str], gray: bool = False) -> float:
    """Verify + warn before escalate/flag (legacy: medium)."""
    has_v = "verify_sender" in trace
    has_w = "warn_user" in trace
    if is_scam:
        if "ignore" in trace:
            return 0.12 if gray else 0.0
        score = 0.0
        if has_v:
            score += 0.5
        if has_w:
            score += 0.5
        if has_v and has_w and ("flag_scam" in trace or "escalate_to_bank" in trace):
            score = 1.0
        return min(1.0, score)
    if "flag_scam" in trace or "block_sender" in trace:
        return 0.28 if gray else 0.0
    if has_v and "ignore" in trace:
        return 1.0
    if "ignore" in trace:
        return 0.94 if gray else 1.0
    return 0.65 if gray else 0.6


def _grade_progressive_thread(is_scam: bool, trace: list[str], row: dict[str, Any], gray: bool = False) -> float:
    """Multi-step thread + timing (legacy: hard)."""
    if not is_scam:
        if "flag_scam" in trace or "escalate_to_bank" in trace:
            return 0.22 if gray else 0.0
        if "ignore" in trace:
            return 0.95 if gray else 1.0
        return 0.7

    if "ignore" in trace:
        return 0.1 if gray else 0.0

    verified_early = any(a == "verify_sender" for a in trace[:3])

    terminal_ok = "flag_scam" in trace or "escalate_to_bank" in trace

    score = 0.0
    if verified_early:
        score += 0.35
    if terminal_ok:
        score += 0.45
    if "warn_user" in trace:
        score += 0.2

    otp_idx = row.get("otp_message_index")
    if otp_idx is not None and int(otp_idx) >= 0 and "verify_sender" not in trace[: int(otp_idx) + 2]:
        score *= 0.7

    score = max(0.0, min(1.0, score))
    if gray and terminal_ok and not verified_early:
        score = max(score, 0.55)
    return score


def _rubric_for_difficulty(
    diff: str,
    is_scam: bool,
    trace: list[str],
    row: dict[str, Any],
    gray: bool,
) -> float:
    """Pick base rubric from scenario difficulty."""
    if diff == "medium":
        return _grade_verify_warn_chain(is_scam, trace, gray)
    if diff == "hard":
        return _grade_progressive_thread(is_scam, trace, row, gray)
    return _grade_single_turn_triage(is_scam, trace, gray)


# ---------------------------------------------------------------------------
# Task-specific graders (semantic pools delegate to core rubrics by row difficulty)
# ---------------------------------------------------------------------------


def _grade_gray_boundary(is_scam: bool, trace: list[str], row: dict[str, Any], gray: bool) -> float:
    """Ambiguous / partial-credit cases — same math as underlying difficulty."""
    diff = str(row.get("difficulty", "easy"))
    return _rubric_for_difficulty(diff, is_scam, trace, row, gray)


def _grade_otp_kyc_pressure(is_scam: bool, trace: list[str], row: dict[str, Any], gray: bool) -> float:
    """OTP / KYC pressure — uses same rubric as scenario difficulty."""
    diff = str(row.get("difficulty", "easy"))
    return _rubric_for_difficulty(diff, is_scam, trace, row, gray)


def _grade_link_phishing_surface(is_scam: bool, trace: list[str], row: dict[str, Any], gray: bool) -> float:
    """Link-bearing phishing — uses same rubric as scenario difficulty."""
    diff = str(row.get("difficulty", "easy"))
    return _rubric_for_difficulty(diff, is_scam, trace, row, gray)


def grade_episode(
    task_id: str,
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    """
    Score a completed episode for the given task.
    ``task_id`` may be a legacy alias (easy/medium/hard).
    Returns a float strictly in (0.0, 1.0).
    """
    canonical = resolve_task_id(task_id)
    row = load_scenario_by_id(scenario_id, data_path)
    true_label = row["true_label"]
    is_scam = true_label == "scam"
    gray = "gray_area" in (row.get("tags") or [])

    if canonical == "single_turn_triage":
        raw = _grade_single_turn_triage(is_scam, action_trace, gray)
    elif canonical == "verify_warn_chain":
        raw = _grade_verify_warn_chain(is_scam, action_trace, gray)
    elif canonical == "progressive_thread":
        raw = _grade_progressive_thread(is_scam, action_trace, row, gray)
    elif canonical == "gray_boundary":
        raw = _grade_gray_boundary(is_scam, action_trace, row, gray)
    elif canonical == "otp_kyc_pressure":
        raw = _grade_otp_kyc_pressure(is_scam, action_trace, row, gray)
    elif canonical == "link_phishing_surface":
        raw = _grade_link_phishing_surface(is_scam, action_trace, row, gray)
    else:
        raise ValueError(f"Unknown task_id: {task_id!r} (canonical: {canonical!r})")
    return _safe_score(raw)


def grade_single_turn_triage(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return grade_episode("single_turn_triage", action_trace, scenario_id, data_path)


def grade_verify_warn_chain(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return grade_episode("verify_warn_chain", action_trace, scenario_id, data_path)


def grade_progressive_thread(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return grade_episode("progressive_thread", action_trace, scenario_id, data_path)


def grade_gray_boundary(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return grade_episode("gray_boundary", action_trace, scenario_id, data_path)


def grade_otp_kyc_pressure(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return grade_episode("otp_kyc_pressure", action_trace, scenario_id, data_path)


def grade_link_phishing_surface(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return grade_episode("link_phishing_surface", action_trace, scenario_id, data_path)


# Legacy names (easy / medium / hard) for older imports and scripts.
def grade_easy(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return grade_episode("easy", action_trace, scenario_id, data_path)


def grade_medium(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return grade_episode("medium", action_trace, scenario_id, data_path)


def grade_hard(
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    return grade_episode("hard", action_trace, scenario_id, data_path)


# Registry: canonical task_id → grader callable (episode-level)
GRADERS: dict[str, object] = {
    "single_turn_triage": grade_single_turn_triage,
    "verify_warn_chain": grade_verify_warn_chain,
    "progressive_thread": grade_progressive_thread,
    "gray_boundary": grade_gray_boundary,
    "otp_kyc_pressure": grade_otp_kyc_pressure,
    "link_phishing_surface": grade_link_phishing_surface,
}

TASK_IDS_WITH_GRADERS: tuple[str, ...] = tuple(GRADERS.keys())


def grade_action(
    task_id: str,
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    """Alias for ``grade_episode`` (episode-level scoring for this env)."""
    return grade_episode(task_id, action_trace, scenario_id, data_path)


__all__ = [
    "GRADERS",
    "MIN_VALID_SCORE",
    "MAX_VALID_SCORE",
    "TASK_IDS_WITH_GRADERS",
    "finalize_episode_score",
    "grade_action",
    "grade_easy",
    "grade_episode",
    "grade_gray_boundary",
    "grade_hard",
    "grade_link_phishing_surface",
    "grade_medium",
    "grade_otp_kyc_pressure",
    "grade_progressive_thread",
    "grade_single_turn_triage",
    "grade_verify_warn_chain",
    "load_scenario_by_id",
    "_grade_gray_boundary",
    "_grade_link_phishing_surface",
    "_grade_otp_kyc_pressure",
    "_grade_progressive_thread",
    "_grade_single_turn_triage",
    "_grade_verify_warn_chain",
    "_safe_score",
]
