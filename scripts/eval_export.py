#!/usr/bin/env python3
"""Export evaluation runs to JSONL or CSV (scenario, trace, grader, task). Not hackathon stdout."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baseline.baseline_agent import BaselineAgent
from env.scam_env import ScamEnv
from graders.scam_grader import grade_episode, load_scenario_by_id
from tasks.easy_task import MAX_STEPS as EASY_MAX
from tasks.hard_task import MAX_STEPS as HARD_MAX
from tasks.medium_task import MAX_STEPS as MEDIUM_MAX

SUCCESS_THRESHOLD = float(os.getenv("SUCCESS_SCORE_THRESHOLD", "0.8"))


def _run_episode_baseline(env: ScamEnv, seed: int | None, scenario_id: str | None) -> dict[str, Any]:
    obs, info = env.reset(seed=seed, scenario_id=scenario_id)
    sid = info["scenario_id"]
    agent = BaselineAgent()
    agent.reset()
    total_r = 0.0
    err: str | None = None
    done = False
    try:
        while not done:
            a = agent.act(obs, env.action_trace)
            obs, reward, done, _ = env.step(a)
            total_r += reward
    except ValueError as e:
        err = str(e)
    score = (
        grade_episode(env.task_id, env.action_trace, sid, env.data_path)
        if err is None
        else 0.0
    )
    row = load_scenario_by_id(sid, env.data_path)
    tags = list(row.get("tags") or [])
    return {
        "scenario_id": sid,
        "task": env.task_id,
        "true_label": row.get("true_label"),
        "tags": tags,
        "gray_area": "gray_area" in tags,
        "action_trace": list(env.action_trace),
        "sum_step_reward": round(total_r, 4),
        "grader_score": round(score, 4),
        "success": err is None and score >= SUCCESS_THRESHOLD,
        "error": err,
    }


def _run_episode_llm(
    env: ScamEnv,
    seed: int | None,
    scenario_id: str | None,
    get_action,
) -> dict[str, Any]:
    obs, info = env.reset(seed=seed, scenario_id=scenario_id)
    sid = info["scenario_id"]
    total_r = 0.0
    err: str | None = None
    done = False
    try:
        while not done:
            a = get_action(obs, env.action_trace)
            obs, reward, done, _ = env.step(a)
            total_r += reward
    except ValueError as e:
        err = str(e)
    except Exception as e:
        err = f"llm_error:{e}"
    score = grade_episode(env.task_id, env.action_trace, sid, env.data_path) if err is None else 0.0
    row = load_scenario_by_id(sid, env.data_path)
    tags = list(row.get("tags") or [])
    return {
        "scenario_id": sid,
        "task": env.task_id,
        "true_label": row.get("true_label"),
        "tags": tags,
        "gray_area": "gray_area" in tags,
        "action_trace": list(env.action_trace),
        "sum_step_reward": round(total_r, 4),
        "grader_score": round(score, 4),
        "success": err is None and score >= SUCCESS_THRESHOLD,
        "error": err,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export eval rows to JSONL or CSV")
    parser.add_argument("--task", choices=["easy", "medium", "hard"], default="easy")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario-id", default=None)
    parser.add_argument("--agent", choices=["baseline", "llm"], default="baseline")
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    parser.add_argument(
        "-o",
        "--output",
        default="-",
        help="Output path, or '-' for stdout (default)",
    )
    args = parser.parse_args()

    max_steps = {"easy": EASY_MAX, "medium": MEDIUM_MAX, "hard": HARD_MAX}[args.task]
    env = ScamEnv(task_id=args.task, max_steps=max_steps)

    get_action = None
    if args.agent == "llm":
        from openai import OpenAI

        import inference as inf

        key = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or ""
        if not key:
            print("HF_TOKEN or API_KEY required for --agent llm", file=sys.stderr)
            raise SystemExit(1)
        client = OpenAI(base_url=inf.API_BASE_URL, api_key=key)

        def get_action(obs: dict[str, Any], trace: list[str]) -> str:
            return inf.get_llm_action(client, obs, trace)

    out_rows: list[dict[str, Any]] = []
    for i in range(args.episodes):
        seed = args.seed + i if args.seed is not None else None
        if args.agent == "baseline":
            row = _run_episode_baseline(env, seed=seed, scenario_id=args.scenario_id)
        else:
            row = _run_episode_llm(env, seed=seed, scenario_id=args.scenario_id, get_action=get_action)
        row["episode_index"] = i
        out_rows.append(row)

    env.close()

    stream = open(args.output, "w", encoding="utf-8", newline="") if args.output != "-" else sys.stdout
    try:
        if args.format == "jsonl":
            for r in out_rows:
                stream.write(json.dumps(r, ensure_ascii=False) + "\n")
        else:
            fieldnames = [
                "episode_index",
                "task",
                "scenario_id",
                "true_label",
                "gray_area",
                "tags",
                "action_trace",
                "sum_step_reward",
                "grader_score",
                "success",
                "error",
            ]
            w = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for r in out_rows:
                flat = {**r, "tags": ";".join(r["tags"]), "action_trace": ";".join(r["action_trace"])}
                w.writerow(flat)
    finally:
        if args.output != "-":
            stream.close()


if __name__ == "__main__":
    main()
