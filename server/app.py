"""
FastAPI app for Hugging Face Spaces / OpenEnv validators.

Run locally:
  uvicorn server.app:app --host 0.0.0.0 --port 7860

HF Spaces set PORT (often 7860).
"""

from __future__ import annotations

import os

from openenv.core.env_server.http_server import create_app

from server.openenv_types import ScamEnvAction, ScamEnvObservation
from server.scam_openenv_environment import ScamOpenEnvEnvironment

# OpenEnv's HTTP handlers call the factory on every /reset and /step; use one instance
# so POST /step continues the same episode (OK for single-worker Spaces).
_shared: ScamOpenEnvEnvironment | None = None


def _scam_env_factory() -> ScamOpenEnvEnvironment:
    global _shared
    if _shared is None:
        _shared = ScamOpenEnvEnvironment()
    return _shared


app = create_app(
    _scam_env_factory,
    ScamEnvAction,
    ScamEnvObservation,
    env_name="scam-detection-env",
)


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
