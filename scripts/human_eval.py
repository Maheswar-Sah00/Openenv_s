#!/usr/bin/env python3
"""Human-readable multi-episode eval (mean reward / grader). Not the hackathon STDOUT protocol."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baseline.baseline_agent import BaselineAgent
from env.scam_env import ScamEnv
from tasks.graders import grade_episode
from tasks.easy_task import MAX_STEPS as EASY_MAX
from tasks.hard_task import MAX_STEPS as HARD_MAX
from tasks.medium_task import MAX_STEPS as MEDIUM_MAX


def run_episode(env: ScamEnv, agent: BaselineAgent, seed: int | None) -> tuple[float, float, str, list[str]]:
    obs, info = env.reset(seed=seed)
    scenario_id = info["scenario_id"]
    agent.reset()
    total_reward = 0.0
    done = False
    while not done:
        action = agent.act(obs, env.action_trace)
        obs, reward, done, _step_info = env.step(action)
        total_reward += reward
    score = grade_episode(env.task_id, env.action_trace, scenario_id, env.data_path)
    return total_reward, score, scenario_id, list(env.action_trace)


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline benchmark — table output")
    parser.add_argument("--task", choices=["easy", "medium", "hard"], default="easy")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    max_steps = {"easy": EASY_MAX, "medium": MEDIUM_MAX, "hard": HARD_MAX}[args.task]
    env = ScamEnv(task_id=args.task, max_steps=max_steps)
    agent = BaselineAgent()

    for i in range(args.episodes):
        r, s, sid, trace = run_episode(env, agent, seed=args.seed + i)
        print(f"episode={i} scenario={sid} reward={r:.3f} grader={s:.3f} actions={trace}")

    env.close()


if __name__ == "__main__":
    main()
