from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from env.models import Action, Observation
from env.reward import compute_step_reward
from tasks.task_registry import resolve_task_id, scenario_in_task_pool


@dataclass
class Scenario:
    id: str
    difficulty: str
    true_label: str
    channel: str
    language: str
    sender_type: str
    messages: list[str]
    link_present: bool
    urgency_score: float
    tags: list[str]
    stage_labels: list[str] = field(default_factory=list)
    otp_message_index: int | None = None

    @property
    def is_scam(self) -> bool:
        return self.true_label == "scam"

    @property
    def is_legitimate(self) -> bool:
        return self.true_label == "legitimate"


def _load_scenarios(path: Path) -> list[Scenario]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[Scenario] = []
    for row in raw:
        msgs = row.get("messages")
        if not msgs:
            msgs = [row["message"]]
        otp_idx = row.get("otp_message_index")
        out.append(
            Scenario(
                id=row["id"],
                difficulty=row["difficulty"],
                true_label=row["true_label"],
                channel=row.get("channel", "sms"),
                language=row.get("language", "en"),
                sender_type=row.get("sender_type", "unknown"),
                messages=list(msgs),
                link_present=bool(row.get("link_present", False)),
                urgency_score=float(row.get("urgency_score", 0.5)),
                tags=list(row.get("tags", [])),
                stage_labels=list(row.get("stage_labels", [])),
                otp_message_index=int(otp_idx) if otp_idx is not None else None,
            )
        )
    return out


def _scenario_row_dict(s: Scenario) -> dict[str, Any]:
    """Dataset-shaped dict for task pool filters."""
    return {
        "id": s.id,
        "difficulty": s.difficulty,
        "true_label": s.true_label,
        "messages": s.messages,
        "tags": s.tags,
        "link_present": s.link_present,
        "otp_message_index": s.otp_message_index,
    }


class ScamEnv:
    """OpenEnv-style fraud analyst simulation."""

    TERMINAL_ACTIONS = frozenset(
        {
            Action.ignore,
            Action.flag_scam,
            Action.block_sender,
            Action.escalate_to_bank,
        }
    )

    def __init__(
        self,
        task_id: str = "easy",
        data_path: Path | None = None,
        max_steps: int = 20,
    ) -> None:
        self.task_id = task_id
        self._canonical_task_id = resolve_task_id(task_id)
        base = Path(__file__).resolve().parent.parent
        self.data_path = data_path or (base / "data" / "scam_dataset.json")
        self._all = _load_scenarios(self.data_path)
        self.max_steps = max_steps
        self._rng: random.Random | None = None
        self._scenario: Scenario | None = None
        self._step_index = 0
        self._revealed = 1
        self._verified = False
        self.action_trace: list[str] = []

    def _pool(self) -> list[Scenario]:
        canon = self._canonical_task_id
        out: list[Scenario] = []
        for s in self._all:
            if scenario_in_task_pool(_scenario_row_dict(s), canon):
                out.append(s)
        return out

    def reset(self, seed: int | None = None, scenario_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        self._rng = random.Random(seed)
        pool = self._pool()
        if not pool:
            raise RuntimeError(f"No scenarios for task {self.task_id}")
        if scenario_id:
            match = [s for s in pool if s.id == scenario_id]
            if not match:
                raise ValueError(f"Unknown scenario_id {scenario_id!r} for task {self.task_id}")
            self._scenario = match[0]
        else:
            self._scenario = self._rng.choice(pool)
        self._step_index = 0
        self.action_trace = []
        self._verified = False
        s = self._scenario
        if s.difficulty == "hard":
            self._revealed = 1
        elif s.difficulty == "medium" and s.is_scam and len(s.messages) > 1:
            self._revealed = 1
        else:
            self._revealed = len(s.messages)
        obs = self._build_observation()
        info = {"scenario_id": s.id, "task_id": self.task_id}
        return obs.as_dict(), info

    def state(self) -> dict[str, Any]:
        if self._scenario is None:
            raise RuntimeError("Call reset() before state()")
        return self._build_observation().as_dict()

    def _risk_factors(self) -> list[str]:
        assert self._scenario is not None
        s = self._scenario
        factors: list[str] = []
        if s.link_present:
            factors.append("link_in_message")
        if s.urgency_score >= 0.75:
            factors.append("high_urgency_language")
        if s.sender_type == "unknown":
            factors.append("unregistered_sender")
        joined = " ".join(s.messages).lower()
        revealed = " ".join(s.messages[: self._revealed]).lower()
        if "otp" in joined:
            factors.append("otp_keyword_present")
        if "kyc" in joined:
            factors.append("kyc_keyword_present")
        if any(x in revealed for x in ("upi", "gpay", "phonepe", "paytm")):
            factors.append("upi_payment_context")
        if any(x in revealed for x in ("gift card", "itunes", "google play card")):
            factors.append("gift_card_request_pattern")
        if any(x in revealed for x in ("remote access", "anydesk", "teamviewer")):
            factors.append("remote_access_software_mention")
        if any(x in revealed for x in ("cryptocurrency", "bitcoin", "usdt", "wallet seed")):
            factors.append("crypto_context")
        if "verify" in revealed and "http" in revealed:
            factors.append("http_verify_combo")
        return factors

    def _build_observation(self) -> Observation:
        assert self._scenario is not None
        s = self._scenario
        hist = s.messages[: self._revealed]
        latest = hist[-1] if hist else ""
        sender_verified: bool | None = None
        if self._verified:
            sender_verified = False if s.is_scam else True
        risk = s.urgency_score
        if self._verified and s.is_scam:
            risk = min(1.0, s.urgency_score + 0.2)
        return Observation(
            case_id=s.id,
            message_text=latest,
            sender_type=s.sender_type,
            channel=s.channel,
            link_present=s.link_present,
            urgency_score=s.urgency_score,
            conversation_history=list(hist),
            sender_verified=sender_verified,
            risk_score=risk,
            risk_factors=self._risk_factors(),
            steps_taken=self._step_index,
            max_episode_steps=self.max_steps,
        )

    def step(self, action: str | Action) -> tuple[dict[str, Any], float, bool, dict[str, Any]]:
        if self._scenario is None:
            raise RuntimeError("Call reset() before step()")
        if isinstance(action, str):
            try:
                act = Action(action)
            except ValueError as e:
                allowed = ", ".join(a.value for a in Action)
                raise ValueError(
                    f"Invalid action {action!r}. Must be one of: {allowed}"
                ) from e
        else:
            act = action
        self.action_trace.append(act.value)

        verification_just_happened = False
        if act == Action.verify_sender and not self._verified:
            self._verified = True
            verification_just_happened = True
            s = self._scenario
            if s.difficulty == "medium" and s.is_scam and len(s.messages) > 1:
                self._revealed = len(s.messages)

        reward = compute_step_reward(
            is_scam=self._scenario.is_scam,
            is_legitimate=self._scenario.is_legitimate,
            action=act,
            verification_just_happened=verification_just_happened,
        )

        self._step_index += 1

        done = act in self.TERMINAL_ACTIONS or self._step_index >= self.max_steps
        if self._scenario.difficulty == "hard" and act not in self.TERMINAL_ACTIONS:
            self._revealed = min(len(self._scenario.messages), self._revealed + 1)
        info = {
            "step": self._step_index,
            "truncated": self._step_index >= self.max_steps and act not in self.TERMINAL_ACTIONS,
        }
        obs = self._build_observation()
        return obs.as_dict(), reward, done, info

    def close(self) -> None:
        """No-op for API parity with containerized / remote envs."""
        return None
