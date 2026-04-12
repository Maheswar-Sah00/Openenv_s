#!/usr/bin/env python3
"""
Scaler Meta PyTorch / OpenEnv Round 1 — root inference.py.

MANDATORY for --agent llm (OpenAI client + env vars from the judge / LiteLLM proxy):
  API_BASE_URL   Injected proxy base URL (do not hardcode another provider in eval).
  API_KEY        Injected key for the proxy (preferred). HF_TOKEN also accepted for local dev.
  MODEL_NAME     Model id for chat completions.

Stdout (per episode), field order must match organizer sample:
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...>

Unless --all-tasks is set, the driver runs at least three full episode blocks (each block is
[START] ... [STEP]* ... [END]) so logs always contain three scored runs for a single --task.

Stay under the ~20 minute judge cap; optional SCAM_ENV_MAX_RUNTIME_SEC (default 1140s).

Optional LLM tuning: SCAM_ENV_LLM_MAX_RETRIES (default 3), SCAM_ENV_LLM_JSON_MODE=1
(response_format json_object + {{"action":"..."}}), SCAM_ENV_LLM_CACHE=1 (dev-only cache).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baseline.baseline_agent import BaselineAgent
from env.models import Action
from env.scam_env import ScamEnv
from tasks.graders import finalize_episode_score, grade_episode
from tasks.task_registry import CANONICAL_TASK_IDS, MAX_STEPS_BY_TASK, TASK_ALIASES

# --- Config (env + argparse) ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
# Judge injects API_KEY; HF_TOKEN for local Hugging Face router — API_KEY first for proxy billing.
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN") or ""


def _default_agent_arg() -> str:
    """Use LLM when keys exist (Phase 2 proxy observes API calls); else baseline for local smoke."""
    a = os.getenv("SCAM_ENV_AGENT")
    if a in ("llm", "baseline"):
        return a
    return "llm" if (os.getenv("API_KEY") or os.getenv("HF_TOKEN")) else "baseline"
BENCHMARK = os.getenv("BENCHMARK", "scam-detection-env")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME") or ""
SUCCESS_SCORE_THRESHOLD = float(os.getenv("SUCCESS_SCORE_THRESHOLD", "0.8"))
TEMPERATURE = float(os.getenv("SCAM_ENV_TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("SCAM_ENV_MAX_TOKENS", "120"))
LLM_MAX_RETRIES = max(1, int(os.getenv("SCAM_ENV_LLM_MAX_RETRIES", "3")))
LLM_JSON_MODE = os.getenv("SCAM_ENV_LLM_JSON_MODE", "").lower() in ("1", "true", "yes")
LLM_CACHE_ENABLED = os.getenv("SCAM_ENV_LLM_CACHE", "").lower() in ("1", "true", "yes")

_LLM_ACTION_CACHE: dict[str, str] = {}

ALLOWED_ACTIONS: tuple[str, ...] = tuple(a.value for a in Action)


def log_start(task: str, env_name: str, model: str) -> None:
    print(f"[START] task={task} env={env_name} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: str | None) -> None:
    err = "null" if error is None else _one_line(error)
    act = _one_line(action)
    print(
        f"[STEP] step={step} action={act} reward={reward:.2f} done={str(done).lower()} error={err}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    # Score already clamped to (0,1) open via finalize_episode_score / grade_episode.
    sc = float(score)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={sc:.2f} rewards={rewards_str}",
        flush=True,
    )


def _one_line(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())[:500]


def parse_action_from_model_text(text: str) -> str:
    """Return exactly one allowed action string or raise ValueError."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty model output")
    low = raw.lower()
    if low in ALLOWED_ACTIONS:
        return low
    for name in sorted(ALLOWED_ACTIONS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", low):
            return name
    raise ValueError(f"unparseable_action:{raw!r}")


SYSTEM_PROMPT = textwrap.dedent(
    """
    You are a bank fraud analyst agent in a simulation. You receive a JSON observation each turn.
    You must output exactly one action from this list (plain text, no JSON, no quotes):
    {actions}

    Rules of thumb:
    - Terminal actions end the episode: ignore, flag_scam, block_sender, escalate_to_bank.
    - verify_sender and warn_user are non-terminal and gather/confirm risk before closing the case.
    - Use observation fields: message_text, conversation_history, sender_type, sender_verified,
      link_present, urgency_score, risk_score, risk_factors, steps_taken, max_episode_steps.

    Reply with exactly one line: the action name only.
    """
).strip().format(actions=", ".join(ALLOWED_ACTIONS))

SYSTEM_PROMPT_JSON = textwrap.dedent(
    """
    You are a bank fraud analyst agent in a simulation. You receive a JSON observation each turn.
    Respond with a single JSON object only, no markdown, no extra keys:
    {{"action": "<one_of_allowed>"}}
    where <one_of_allowed> is exactly one of: {actions}

    Rules of thumb:
    - Terminal actions end the episode: ignore, flag_scam, block_sender, escalate_to_bank.
    - verify_sender and warn_user are non-terminal when you need more certainty.
    """
).strip().format(actions=", ".join(ALLOWED_ACTIONS))

_JSON_USER_HINT = 'Return only JSON: {"action": "..."}'
_PLAIN_USER_HINT = "Choose the next action (one token from the allowed list)."


def _llm_cache_key(observation: dict[str, Any], trace: list[str]) -> str:
    blob = json.dumps(observation, sort_keys=True, ensure_ascii=False) + "\n" + json.dumps(trace)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _action_from_json_content(text: str) -> str:
    obj = json.loads(text)
    act = obj.get("action") if isinstance(obj, dict) else None
    if act is None and isinstance(obj, dict):
        act = obj.get("Action")
    if act is None:
        raise ValueError("json_missing_action_key")
    return parse_action_from_model_text(str(act))


def get_llm_action(client: Any, observation: dict[str, Any], trace: list[str]) -> str:
    from openai import OpenAI

    assert isinstance(client, OpenAI)
    json_mode = LLM_JSON_MODE
    if LLM_CACHE_ENABLED:
        ck = _llm_cache_key(observation, trace)
        hit = _LLM_ACTION_CACHE.get(ck)
        if hit is not None:
            return hit

    system = SYSTEM_PROMPT_JSON if json_mode else SYSTEM_PROMPT
    hint = _JSON_USER_HINT if json_mode else _PLAIN_USER_HINT
    obs_json = json.dumps(observation, ensure_ascii=False)
    trace_repr = repr(trace)
    user = textwrap.dedent(
        """
        Current observation (JSON):
        {obs}

        Actions taken so far: {tr}
        {hint}
        """
    ).format(obs=obs_json, tr=trace_repr, hint=hint).strip()

    kwargs: dict[str, Any] = dict(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        stream=False,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_err: Exception | None = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            completion = client.chat.completions.create(**kwargs)
            text = (completion.choices[0].message.content or "").strip()
            if json_mode:
                out = _action_from_json_content(text)
            else:
                out = parse_action_from_model_text(text)
            if LLM_CACHE_ENABLED:
                _LLM_ACTION_CACHE[_llm_cache_key(observation, trace)] = out
            return out
        except Exception as e:
            last_err = e
            if attempt >= LLM_MAX_RETRIES - 1:
                raise
    assert last_err is not None
    raise last_err


def run_episode_protocol(
    *,
    task: str,
    seed: int | None,
    scenario_id: str | None,
    agent_mode: str,
    client: Any | None,
    model_label: str,
) -> None:
    max_steps = MAX_STEPS_BY_TASK[task]
    env = ScamEnv(task_id=task, max_steps=max_steps)
    rewards: list[float] = []
    steps_taken = 0
    success = False
    sid: str | None = None
    episode_error: str | None = None
    grader_val: float | None = None

    log_start(task=task, env_name=BENCHMARK, model=model_label)

    try:
        obs, info = env.reset(seed=seed, scenario_id=scenario_id)
        sid = info["scenario_id"]
        baseline = BaselineAgent()
        done = False
        step_n = 0

        while not done:
            step_n += 1
            action_str = ""

            try:
                if agent_mode == "llm":
                    if client is None:
                        raise RuntimeError("LLM agent selected but OpenAI client is not configured")
                    action_str = get_llm_action(client, obs, env.action_trace)
                else:
                    action_str = baseline.act(obs, env.action_trace)

                obs, reward, step_done, _info = env.step(action_str)
                rewards.append(reward)
                steps_taken = step_n
                log_step(step_n, action_str, reward, step_done, None)
                done = step_done
            except ValueError as e:
                episode_error = str(e)
                rewards.append(0.0)
                steps_taken = step_n
                log_step(step_n, action_str or "invalid_action", 0.0, True, episode_error)
                done = True
                break
            except Exception as e:
                episode_error = str(e)
                rewards.append(0.0)
                steps_taken = step_n
                log_step(step_n, action_str or "error", 0.0, True, episode_error)
                print(f"[DEBUG] step exception: {e}", file=sys.stderr, flush=True)
                done = True
                break

        if sid is not None and episode_error is None:
            grader_val = grade_episode(task, env.action_trace, sid, env.data_path)
            success = grader_val >= SUCCESS_SCORE_THRESHOLD
        else:
            success = False
    except Exception as e:
        success = False
        episode_error = str(e)
        print(f"[DEBUG] episode exception: {e}", file=sys.stderr, flush=True)
    finally:
        try:
            env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", file=sys.stderr, flush=True)
        end_score = finalize_episode_score(grader_val)
        log_end(success=success, steps=steps_taken, score=end_score, rewards=rewards)
        sys.stdout.flush()
        if os.getenv("SCAM_ENV_DEBUG") and grader_val is not None and sid is not None:
            print(f"[DEBUG] grader_score={grader_val:.2f} scenario={sid}", file=sys.stderr, flush=True)


def main() -> None:
    t0 = time.monotonic()
    max_runtime_s = float(os.getenv("SCAM_ENV_MAX_RUNTIME_SEC", "1140"))

    parser = argparse.ArgumentParser(description="Scam env — hackathon STDOUT protocol")
    _task_choices = list(CANONICAL_TASK_IDS) + list(TASK_ALIASES.keys())
    parser.add_argument(
        "--task",
        choices=sorted(set(_task_choices)),
        default=os.getenv("SCAM_ENV_TASK", "easy"),
    )
    parser.add_argument("--seed", type=int, default=int(os.getenv("SCAM_ENV_SEED", "42")))
    parser.add_argument("--scenario-id", default=os.getenv("SCAM_ENV_SCENARIO_ID") or None)
    parser.add_argument("--episodes", type=int, default=int(os.getenv("SCAM_ENV_EPISODES", "1")))
    parser.add_argument(
        "--all-tasks",
        action="store_true",
        help="Run one episode per canonical task (six tasks; pre-submission smoke test)",
    )
    parser.add_argument(
        "--agent",
        choices=["llm", "baseline"],
        default=_default_agent_arg(),
        help="llm uses OpenAI client + API_BASE_URL/API_KEY (default llm if API_KEY or HF_TOKEN set)",
    )
    args = parser.parse_args()

    client = None
    model_label = MODEL_NAME if args.agent == "llm" else "baseline-rules"
    if args.agent == "llm":
        try:
            from openai import OpenAI
        except ImportError as e:
            print("Install openai: pip install openai", file=sys.stderr)
            raise SystemExit(1) from e
        api_key = os.getenv("API_KEY") or os.getenv("HF_TOKEN") or ""
        if not api_key:
            print("API_KEY or HF_TOKEN required for --agent llm", file=sys.stderr)
            raise SystemExit(1)
        base_url = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
        client = OpenAI(base_url=base_url, api_key=api_key)

    if LOCAL_IMAGE_NAME:
        print(f"[DEBUG] LOCAL_IMAGE_NAME={LOCAL_IMAGE_NAME} (not used; in-process ScamEnv)", file=sys.stderr)

    if args.all_tasks:
        task_list = list(CANONICAL_TASK_IDS)
        episodes_per = 1
    else:
        task_list = [args.task]
        episodes_per = args.episodes

    min_protocol_cycles = 3
    n_tasks = len(task_list)
    if n_tasks * episodes_per < min_protocol_cycles:
        episodes_per = max(episodes_per, math.ceil(min_protocol_cycles / n_tasks))

    for task in task_list:
        if time.monotonic() - t0 > max_runtime_s:
            print("[DEBUG] Stopping: SCAM_ENV_MAX_RUNTIME_SEC exceeded", file=sys.stderr)
            raise SystemExit(2)
        for ep in range(episodes_per):
            if time.monotonic() - t0 > max_runtime_s:
                print("[DEBUG] Stopping: SCAM_ENV_MAX_RUNTIME_SEC exceeded", file=sys.stderr)
                raise SystemExit(2)
            seed = args.seed + ep if args.seed is not None else None
            run_episode_protocol(
                task=task,
                seed=seed,
                scenario_id=args.scenario_id,
                agent_mode=args.agent,
                client=client,
                model_label=model_label,
            )


if __name__ == "__main__":
    main()
