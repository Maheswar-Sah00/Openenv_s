#!/usr/bin/env python3
"""Verify a deployed HF Space (or local uvicorn): POST /reset and POST /step return 200."""

from __future__ import annotations

import argparse
import os
import sys

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test OpenEnv HTTP endpoints")
    parser.add_argument(
        "base_url",
        nargs="?",
        default=os.getenv("HF_SPACE_URL", ""),
        help="Space base URL, e.g. https://user-myenv.hf.space (or set HF_SPACE_URL)",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    base = (args.base_url or "").strip().rstrip("/")
    if not base:
        print(
            "Usage: python scripts/hf_smoke_check.py https://YOUR-SPACE.hf.space\n"
            "   or: set HF_SPACE_URL",
            file=sys.stderr,
        )
        raise SystemExit(2)

    session = requests.Session()
    r = session.post(f"{base}/reset", json={}, timeout=args.timeout)
    print(f"POST /reset -> HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:500], file=sys.stderr)
        raise SystemExit(1)

    step_body = {"action": {"action": "verify_sender", "metadata": {}}}
    r2 = session.post(f"{base}/step", json=step_body, timeout=args.timeout)
    print(f"POST /step  -> HTTP {r2.status_code}")
    if r2.status_code != 200:
        print(r2.text[:500], file=sys.stderr)
        raise SystemExit(1)

    print("OK: Space responds like a healthy OpenEnv server.")


if __name__ == "__main__":
    main()
