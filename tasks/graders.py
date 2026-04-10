# tasks/graders.py
# All three task graders in one module (Phase 2 / static discovery friendly).
# Deterministic: same trajectory + scenario → same score. NO LLM judges.

from __future__ import annotations

from pathlib import Path

from tasks.database import load_scenario_by_id

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


def _raw_score_easy(is_scam: bool, trace: list[str], gray: bool = False) -> float:
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


def _raw_score_medium(is_scam: bool, trace: list[str], gray: bool = False) -> float:
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


def _raw_score_hard(is_scam: bool, trace: list[str], row: dict, gray: bool = False) -> float:
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


def grade_episode(
    task_id: str,
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    row = load_scenario_by_id(scenario_id, data_path)
    true_label = row["true_label"]
    is_scam = true_label == "scam"
    gray = "gray_area" in (row.get("tags") or [])

    if task_id == "easy":
        raw = _raw_score_easy(is_scam, action_trace, gray)
    elif task_id == "medium":
        raw = _raw_score_medium(is_scam, action_trace, gray)
    elif task_id == "hard":
        raw = _raw_score_hard(is_scam, action_trace, row, gray)
    else:
        raise ValueError(f"Unknown task_id: {task_id}")
    return _safe_score(raw)


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


# Registry: task_id → grader callable (episode-level)
GRADERS: dict[str, object] = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
}

TASK_IDS_WITH_GRADERS: tuple[str, ...] = tuple(GRADERS.keys())


def grade_action(
    task_id: str,
    action_trace: list[str],
    scenario_id: str,
    data_path: Path | None = None,
) -> float:
    """Score a completed episode; same as ``grade_episode``."""
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
    "grade_hard",
    "grade_medium",
    "load_scenario_by_id",
    "_raw_score_easy",
    "_raw_score_hard",
    "_raw_score_medium",
    "_safe_score",
]
