---
title: AI Scam Detection OpenEnv
emoji: 🛡️
colorFrom: gray
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: OpenEnv FastAPI server for fraud analyst simulation.
tags:
  - openenv
  - fraud-detection
  - reinforcement-learning
---

# Scam Detection OpenEnv

OpenEnv-compatible environment for **bank/fintech fraud analyst** simulation: discrete actions over a structured observation, step rewards for RL-style training, and a deterministic episode grader. Agents run via [`inference.py`](inference.py) (stdout protocol) or against the **FastAPI** server in [`server/`](server/).

---

## Requirements

- **Python 3.11+** (matches [`Dockerfile`](Dockerfile))
- **pip**
- Optional: **Docker** (same image as Hugging Face Space)
- Optional: **`openenv-core[cli]`** for `openenv validate`

---

## Install

Clone the repo and install dependencies from the repository root (`scam-env/` — the directory that contains `requirements.txt` and `Dockerfile`).

```bash
cd scam-env
pip install -r requirements.txt
```

You do not need to set `PYTHONPATH` for `inference.py`; it adds the project root automatically.

---

## Run locally

### API server

```bash
uvicorn server.app:app --host 127.0.0.1 --port 7860
```

Open [http://127.0.0.1:7860/docs](http://127.0.0.1:7860/docs) for interactive API docs. Main endpoints: `POST /reset`, `POST /step`, `GET /state`.

### Inference (baseline, no API keys)

```bash
python inference.py --agent baseline --task easy --seed 42
```

For a **single** `--task`, the driver runs **at least three** full episodes by default (three `[START]` … `[END]` blocks on stdout), even if you pass `--episodes 1`.

Run one episode per canonical task (six tasks):

```bash
python inference.py --agent baseline --all-tasks --seed 42
```

### Inference (LLM agent)

Set an OpenAI-compatible base URL and key (hackathon eval typically injects these):

| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | Base URL for chat completions (e.g. LiteLLM proxy) |
| `API_KEY` | API key (preferred) |
| `HF_TOKEN` | Fallback for local Hugging Face router |
| `MODEL_NAME` | Model id for chat completions |

**Bash:**

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export API_KEY="your_token_here"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
python inference.py --agent llm --task easy --seed 42
```

**PowerShell:**

```powershell
$env:API_BASE_URL = "https://router.huggingface.co/v1"
$env:API_KEY = "your_token_here"
$env:MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"
python inference.py --agent llm --task easy --seed 42
```

Optional: `SCAM_ENV_AGENT=baseline` or `llm` overrides the default agent choice. See [`inference.py`](inference.py) for `SCAM_ENV_*` tuning (timeouts, retries, JSON mode, debug).

---

## Docker

```bash
docker build -t scam-detection-env .
docker run --rm -p 7860:7860 -e PORT=7860 scam-detection-env
```

Run inference inside the image:

```bash
docker run --rm scam-detection-env python inference.py --agent baseline --task easy --seed 42
```

---

## Validate and test

| Command | Purpose |
|---------|---------|
| `python -m py_compile inference.py` | Quick syntax check |
| `python scripts/verify_task_graders.py` | Task / grader manifest sanity check |
| `python -m unittest tests.test_task_graders -v` | Grader + `openenv.yaml` / `task_graders.json` tests |
| `openenv validate` | Requires `pip install "openenv-core[cli]"` — checks [`openenv.yaml`](openenv.yaml) |

**Full submission-style check** (HF ping, `docker build`, `openenv validate`, then local grader tests): run [`scripts/validate-submission.sh`](scripts/validate-submission.sh) with your Space URL, or [`validator.bash`](validator.bash) from repo root on Git Bash / WSL / Linux:

```bash
./validator.bash https://YOUR-USER-YOUR-SPACE.hf.space
```

Omit the URL to run only the local grader / unittest step. On Windows without Bash, run the Python commands in the table above and `scripts/validate-submission.sh` from Git Bash if available.

---

## Reference

- **Manifest:** [`openenv.yaml`](openenv.yaml) — tasks, actions, observation keys.
- **Grading:** [`tasks/graders.py`](tasks/graders.py) — `GRADERS`, `grade_episode`.
- **Task ids and pools:** [`tasks/task_registry.py`](tasks/task_registry.py).
- **Dataset:** [`data/scam_dataset.json`](data/scam_dataset.json); loaders in [`tasks/database.py`](tasks/database.py).

**Stdout protocol** (per episode, in order): `[START]`, one or more `[STEP]`, `[END]`. On `[END]`, `score=` uses two decimal places; values stay strictly inside (0, 1). Implementation: `log_start`, `log_step`, `log_end` in [`inference.py`](inference.py).

**Hackathon / judge:** use Docker + `inference.py` as above; do not hardcode private API URLs or keys for official eval. For extra checks, see [`scripts/validate-submission.sh`](scripts/validate-submission.sh) and [`scripts/hf_smoke_check.py`](scripts/hf_smoke_check.py).

**Scripts:** dataset generate/validate/merge and exports live under [`scripts/`](scripts/) (`--help` on each script).

---

## Hugging Face Space

This repo is intended to deploy as a **Docker** Space on Hugging Face (port **7860**, app from [`server/app.py`](server/app.py)). After deploy, the public URL is typically `https://<user>-<space>.hf.space`.

Health check (`POST /reset` with empty JSON body):

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST "https://YOUR-SPACE.hf.space/reset" \
  -H "Content-Type: application/json" -d "{}"
```

PowerShell:

```powershell
Invoke-WebRequest -Uri "https://YOUR-SPACE.hf.space/reset" -Method POST `
  -ContentType "application/json" -Body "{}" | Select-Object -ExpandProperty StatusCode
```

---
