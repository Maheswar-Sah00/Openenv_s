"""Pydantic Action/Observation for OpenEnv HTTP API (extends openenv base types)."""

from __future__ import annotations

from typing import Any

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class ScamEnvAction(Action):
    """Discrete analyst action (JSON: {\"action\": \"verify_sender\", \"metadata\": {}})."""

    action: str = Field(
        ...,
        description="One of: ignore, verify_sender, warn_user, flag_scam, block_sender, escalate_to_bank",
    )


class ScamEnvObservation(Observation):
    """Observation returned by reset/step; includes OpenEnv fields done/reward plus case view."""

    observation_schema_version: str = Field(default="1.1")
    case_id: str = Field(default="")
    message_text: str = Field(default="")
    sender_type: str = Field(default="unknown")
    channel: str = Field(default="sms")
    link_present: bool = Field(default=False)
    urgency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    conversation_history: list[str] = Field(default_factory=list)
    sender_verified: bool | None = Field(default=None)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_factors: list[str] = Field(default_factory=list)
    steps_taken: int = Field(default=0, ge=0)
    max_episode_steps: int = Field(default=20, ge=1)
    terminal_actions: tuple[str, ...] = Field(
        default=("ignore", "flag_scam", "block_sender", "escalate_to_bank")
    )
    scenario_id: str = Field(default="", description="Same as case_id; for graders / logging")


class ScamEnvState(State):
    """Episode state exposed via /state."""

    task_id: str = Field(default="easy")
    action_trace: list[str] = Field(default_factory=list)
