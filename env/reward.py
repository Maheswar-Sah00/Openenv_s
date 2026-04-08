"""Step rewards: shaped signals for training (separate from task grader scores)."""

from __future__ import annotations

from env.models import Action


def compute_step_reward(
    *,
    is_scam: bool,
    is_legitimate: bool,
    action: Action,
    verification_just_happened: bool,
) -> float:
    """Return immediate reward for the last action."""
    if action == Action.verify_sender:
        return 0.3 if verification_just_happened else 0.1

    if action == Action.warn_user:
        return 0.5 if is_scam else -0.1

    if action == Action.ignore:
        return 0.4 if is_legitimate else -1.0

    if action == Action.flag_scam:
        return 1.0 if is_scam else -0.5

    if action == Action.block_sender:
        return 0.7 if is_scam else -0.6

    if action == Action.escalate_to_bank:
        if is_scam:
            return 1.0
        return -0.3 if is_legitimate else 0.4

    return 0.0
