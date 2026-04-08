"""
HTTP client for the scam-detection OpenEnv server (HF Space / local uvicorn).

Usage:
  from client import ScamEnvHTTPClient
  with ScamEnvHTTPClient(base_url="https://your-space.hf.space") as c:
      r = c.reset({})
      r = c.step({"action": {"action": "verify_sender", "metadata": {}}})

For offline batch metrics (JSONL/CSV), see scripts/eval_export.py.
"""

from __future__ import annotations

from typing import Any

import requests


class ScamEnvHTTPClient:
    def __init__(self, base_url: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._s = requests.Session()

    def close(self) -> None:
        self._s.close()

    def __enter__(self) -> ScamEnvHTTPClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def reset(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self._s.post(
            f"{self.base_url}/reset",
            json=body or {},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def step(self, body: dict[str, Any]) -> dict[str, Any]:
        r = self._s.post(f"{self.base_url}/step", json=body, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def state(self) -> dict[str, Any]:
        r = self._s.get(f"{self.base_url}/state", timeout=self.timeout)
        r.raise_for_status()
        return r.json()
