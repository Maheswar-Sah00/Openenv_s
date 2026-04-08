"""OpenEnv Environment adapter wrapping in-repo ScamEnv."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from env.scam_env import ScamEnv
from server.openenv_types import ScamEnvAction, ScamEnvObservation, ScamEnvState


def _task_max_steps(task: str) -> int:
    from tasks.easy_task import MAX_STEPS as E
    from tasks.hard_task import MAX_STEPS as H
    from tasks.medium_task import MAX_STEPS as M

    return {"easy": E, "medium": M, "hard": H}.get(task, E)


class ScamOpenEnvEnvironment(Environment[ScamEnvAction, ScamEnvObservation, ScamEnvState]):
    """HTTP-facing environment; delegates to ScamEnv."""

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__(transform=None, rubric=None)
        self._task = os.getenv("SCAM_ENV_TASK", "easy")
        self._core = ScamEnv(task_id=self._task, max_steps=_task_max_steps(self._task))
        self._state = ScamEnvState(episode_id=str(uuid4()), step_count=0, task_id=self._task)
        self._last_scenario_id: str | None = None

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> ScamEnvObservation:
        self._reset_rubric()
        scenario_id = kwargs.get("scenario_id")
        obs, info = self._core.reset(seed=seed, scenario_id=scenario_id)
        self._last_scenario_id = info["scenario_id"]
        self._state = ScamEnvState(
            episode_id=episode_id or self._last_scenario_id or str(uuid4()),
            step_count=0,
            task_id=self._task,
            action_trace=list(self._core.action_trace),
        )
        return self._wrap_obs(obs, reward=0.0, done=False)

    def step(
        self,
        action: ScamEnvAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> ScamEnvObservation:
        obs, reward, done, _info = self._core.step(action.action)
        self._state.step_count = len(self._core.action_trace)
        self._state.action_trace = list(self._core.action_trace)
        return self._wrap_obs(obs, reward=float(reward), done=bool(done))

    @property
    def state(self) -> ScamEnvState:
        self._state.action_trace = list(self._core.action_trace)
        self._state.step_count = len(self._core.action_trace)
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="scam-detection-env",
            description="AI scam detection & response training simulation",
            version="1.0.0",
        )

    def close(self) -> None:
        self._core.close()

    def _wrap_obs(self, obs: dict[str, Any], *, reward: float, done: bool) -> ScamEnvObservation:
        return ScamEnvObservation(
            done=done,
            reward=reward,
            metadata={},
            observation_schema_version=obs.get("observation_schema_version", "1.1"),
            case_id=obs.get("case_id", ""),
            message_text=obs.get("message_text", ""),
            sender_type=obs.get("sender_type", "unknown"),
            channel=obs.get("channel", "sms"),
            link_present=bool(obs.get("link_present", False)),
            urgency_score=float(obs.get("urgency_score", 0.0)),
            conversation_history=list(obs.get("conversation_history") or []),
            sender_verified=obs.get("sender_verified"),
            risk_score=float(obs.get("risk_score", 0.0)),
            risk_factors=list(obs.get("risk_factors") or []),
            steps_taken=int(obs.get("steps_taken", 0)),
            max_episode_steps=int(obs.get("max_episode_steps", 20)),
            terminal_actions=tuple(obs.get("terminal_actions") or ("ignore", "flag_scam", "block_sender", "escalate_to_bank")),
            scenario_id=obs.get("case_id", ""),
        )
