from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Action(str, Enum):
    ignore = "ignore"
    verify_sender = "verify_sender"
    warn_user = "warn_user"
    flag_scam = "flag_scam"
    block_sender = "block_sender"
    escalate_to_bank = "escalate_to_bank"


class Observation(BaseModel):
    observation_schema_version: str = "1.1"
    case_id: str
    message_text: str
    sender_type: str
    channel: str
    link_present: bool
    urgency_score: float = Field(ge=0.0, le=1.0)
    conversation_history: list[str]
    sender_verified: bool | None = None
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_factors: list[str] = Field(default_factory=list)
    steps_taken: int = Field(ge=0, description="Actions taken this episode so far")
    max_episode_steps: int = Field(ge=1, description="Step budget before forced truncation")
    terminal_actions: tuple[str, ...] = Field(
        default=("ignore", "flag_scam", "block_sender", "escalate_to_bank")
    )

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: dict[str, Any] = Field(default_factory=dict)
