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

# AI Scam Detection & Response Training Environment

Python **OpenEnv-style** simulation for training and evaluating agents on **fraud-analyst-style** decisions: triage messages, verify senders, warn customers, flag scams, and escalate.

## Environment design

### Problem

The agent plays a **bank/fintech fraud analyst**. Each episode is one **case**: a message or thread arrives, the agent chooses **actions**, the environment updates what is visible (verification results, unfolding thread), and returns **step rewards** plus a **terminal grader score** (0.0–1.0) for the hackathon task.

### Observation (state)

Agents only see the fields below (see [`openenv.yaml`](openenv.yaml) for the schema version).

| Field | Meaning |
|--------|---------|
| `case_id` | Stable scenario id (for logging; graders reload metadata by id). |
| `message_text` | Latest visible line in the thread. |
| `conversation_history` | All lines revealed so far. |
| `sender_type` | e.g. `unknown`, `bank_official`. |
| `channel` | `sms`, `email`, `whatsapp`, `in_app`. |
| `link_present` | Whether the visible content references a link. |
| `urgency_score` | 0–1 heuristic “pressure” in the scenario data. |
| `sender_verified` | `null` until `verify_sender`; then `true`/`false` depending on ground truth. |
| `risk_score` | Analyst-facing score (rises after failed verification on scams). |
| `risk_factors` | Explainability strings (e.g. `otp_keyword_present`, `upi_payment_context`). |
| `steps_taken` | Number of actions executed so far this episode. |
| `max_episode_steps` | Step budget before truncation. |
| `terminal_actions` | Tuple of action names that end the episode. |

**Hidden from the agent:** dataset `true_label`, internal stage labels — used only for rewards/graders.

**Dataset:** Default messages are **synthetic** (educational patterns). Regenerate with `python scripts/generate_dataset.py` and validate with `python scripts/validate_dataset.py`. **Schema 1.1** adds the step-budget fields above so any agent can reason about the horizon without extra wrappers.

**Combining external data (e.g. Kaggle SMS spam / phishing CSV):** download files locally (respect **licenses** — do not redistribute restricted data in your repo). Merge into `data/scam_dataset.json` with:

```bash
python scripts/merge_external_datasets.py \
  --input path/to/sms.csv \
  --format csv \
  --text-column v2 \
  --label-column v1 \
  --scam-values spam,1 \
  --legit-values ham,0
```

Use `--input` multiple times to combine several files. `--format jsonl` / `json_array` use `--json-text` / `--json-label`. Full env rows (same keys as `scam_dataset.json`) can be merged with `--format native`. New rows are **single-turn** and default to **difficulty=easy**; duplicates (same normalized first message) are skipped. Use `--dry-run` to preview counts, `--output` to write somewhere other than the default `data/scam_dataset.json`.

### Actions

`ignore` · `verify_sender` · `warn_user` · `flag_scam` · `block_sender` · `escalate_to_bank`

Terminal actions (episode ends): `ignore`, `flag_scam`, `block_sender`, `escalate_to_bank`.

### Rewards (step-level, RL-shaped)

Implemented in [`env/reward.py`](env/reward.py). Examples: verification **+0.3** when identity check completes, correct scam flag **+1.0**, false alarm on legitimate **−0.5**, missed scam via `ignore` **−1.0`.

These rewards are **dense** for learning; they are **not** the official competition scalar.

### Task grader (0.0–1.0)

[`graders/scam_grader.py`](graders/scam_grader.py) maps **(task, action trace, scenario_id)** to a deterministic score in **[0, 1]**:

- **Easy:** scam → flag/escalate/block; legitimate → avoid false flags.
- **Medium:** scams require **verify_sender** and **warn_user**; full credit if also flag/escalate.
- **Hard:** early verification, user warning, terminal escalation/flag; OTP-index metadata can reduce score if verification is too late.

Scenarios tagged **`gray_area`** in [`data/scam_dataset.json`](data/scam_dataset.json) use **partial credit** for ambiguous outcomes (e.g. false positives on tricky legitimate messages, or “soft” scams) so metrics reflect analyst-style judgment under uncertainty.

### Episode flow

1. `reset(seed?, scenario_id?)` → observation dict + `info` (`scenario_id`, `task_id`).
2. Repeat `step(action)` until `done` or `max_steps`.
3. Call `grade_episode(task_id, action_trace, scenario_id)`.

**Reveal rules**

- **Easy / single-turn:** full thread visible immediately.
- **Medium (scam, multi-line):** only the first line until `verify_sender`, then the rest.
- **Hard:** thread **unfolds one line per non-terminal step** (time pressure); the thread does **not** advance after a terminal action, so the final observation matches the decision state.

**Invalid actions:** `step("not_an_action")` raises `ValueError` with the allowed action list (helps judge integrations fail fast).

## Quick start (local)

### Hackathon `inference.py` (mandatory STDOUT protocol)

`inference.py` prints **only** these line types to **stdout** (per episode), in order:

1. `[START] task=<task> env=<benchmark> model=<model_name>`
2. `[STEP] step=<n> action=<str> reward=<0.00> done=<true|false> error=<msg|null>`
3. `[END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...>` — `score` is the task grader in **[0, 1]** (three decimals), or `0.000` if grading did not run.

**Mandatory for LLM submission:** set **`API_BASE_URL`**, **`MODEL_NAME`**, and **`HF_TOKEN`** (or `API_KEY`); inference uses the **OpenAI** Python client against that base URL.

This matches the organizer pattern (OpenAI client + structured logs). **Differences from a Docker-only sample:** this repo runs **`ScamEnv` in-process** (same Python process); `LOCAL_IMAGE_NAME` / `IMAGE_NAME` are accepted for compatibility but not required. `env.close()` is a no-op.

**Smoke test all three tasks** (one episode each): `python inference.py --agent baseline --all-tasks --seed 42`

**Runtime cap:** `SCAM_ENV_MAX_RUNTIME_SEC` (default **1140**, i.e. 19 minutes) stops further episodes with exit code **2** so a long run stays under typical **~20 minute** judge limits.

**Baseline (no API key):**

```bash
cd scam-env
pip install -r requirements.txt
python inference.py --agent baseline --task easy --episodes 1 --seed 42
```

**LLM agent (OpenAI-compatible API, e.g. Hugging Face router):**

```bash
set HF_TOKEN=your_token_here
set API_BASE_URL=https://router.huggingface.co/v1
set MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
python inference.py --agent llm --task easy --episodes 1 --seed 42
```

Other env vars: `BENCHMARK` (default `scam-detection-env`), `SUCCESS_SCORE_THRESHOLD` (default `0.8`), `SCAM_ENV_TASK`, `SCAM_ENV_SEED`, `SCAM_ENV_EPISODES`, `SCAM_ENV_DEBUG=1` (stderr grader hint after `[END]`), `SCAM_ENV_MAX_RUNTIME_SEC`.

**LLM robustness (optional):** `SCAM_ENV_LLM_MAX_RETRIES` (default `3`), `SCAM_ENV_LLM_JSON_MODE=1` (JSON `{"action":"..."}` + `response_format`), `SCAM_ENV_LLM_CACHE=1` (in-process cache for repeated obs/trace; dev only).

### Human-readable table (development)

```bash
python scripts/human_eval.py --task easy --episodes 5 --seed 42
```

### Structured eval export (JSONL / CSV)

```bash
python scripts/eval_export.py --task easy --episodes 20 --seed 42 --format jsonl -o results.jsonl
python scripts/eval_export.py --task medium --episodes 10 --format csv -o results.csv
```

Rows include `scenario_id`, `action_trace`, `grader_score`, `gray_area` (dataset tag), `success` vs `SUCCESS_SCORE_THRESHOLD`. Use `--agent llm` with `HF_TOKEN` set for LLM runs.

### CI (GitHub Actions)

On push/PR to `main` or `master`, [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs: `pip install`, `python inference.py --agent baseline --all-tasks`, `openenv validate`, `scripts/validate_dataset.py`, and `docker build`.

## Judge workflow (Docker)

**HF Space / OpenEnv (default image command):** the container runs **FastAPI** (`uvicorn server.app:app`) so `POST /reset` returns HTTP 200 (required by the organizer validator).

```bash
cd scam-env
docker build -t scam-detection-env .
docker run --rm -p 7860:7860 -e PORT=7860 scam-detection-env
# In another shell:
curl -s -X POST http://127.0.0.1:7860/reset -H "Content-Type: application/json" -d "{}"
```

**Offline inference (hackathon STDOUT protocol, no HTTP):**

```bash
docker run --rm scam-detection-env python inference.py --agent baseline --task easy --episodes 1
```

Override the container command in Docker / HF if you only need `inference.py`.

## Organizer pre-check script (`validate-submission.sh`)

The template script runs **three checks**:

| Step | What it does | Your repo |
|------|----------------|-----------|
| 1 | `curl -X POST $PING_URL/reset -d '{}'` → **200** | Served by **`server/app.py`** (OpenEnv FastAPI) when the Space is up. |
| 2 | `docker build` on repo root (or `server/`) | Uses root [`Dockerfile`](Dockerfile). |
| 3 | `openenv validate` | Needs [`openenv.yaml`](openenv.yaml) (`spec_version`, `app: server.app:app`, …), plus layout: `models.py`, `client.py`, `server/*`. Install CLI: `pip install "openenv-core[cli]"`. |

Copy of the script: [`scripts/validate-submission.sh`](scripts/validate-submission.sh). On Linux/macOS: `chmod +x scripts/validate-submission.sh` then run with your Space URL.

**HTTP step body (for manual tests):** `POST /step` with JSON:

```json
{"action": {"action": "verify_sender", "metadata": {}}}
```

## Hugging Face Spaces

The YAML block at the top of this README configures the Space card when this repo is used as a **Docker** Space (`sdk: docker`, `app_port: 7860`).

### Create the Space (UI)

1. Log in at [huggingface.co](https://huggingface.co) → **Spaces** → **Create new Space**.
2. Name the Space, set visibility (**Public** if judges must ping it), and choose SDK **Docker**.
3. Under **Repository**, select **Import from GitHub** (or GitLab) and pick the repo whose **root** is this project (same folder as `Dockerfile` and `openenv.yaml`).  
   - If the env lives in a **subfolder** of a monorepo, either move it to root for the Space or use a branch/submodule layout HF can build from root.
4. Leave **Container port** at **7860** (matches [`Dockerfile`](Dockerfile) and [`openenv.yaml`](openenv.yaml)).
5. Optional: **Settings → Repository secrets / Variables** → add `SCAM_ENV_TASK` = `easy`, `medium`, or `hard` (default in the image is `easy`).
6. Wait for **Building** → **Running**. Open `https://<your-username>-<space-name>.hf.space/docs` for the FastAPI UI.

### Push from your PC (git → Space)

Use this when the Space already exists (e.g. [Docker Space on the Hub](https://huggingface.co/docs/hub/spaces-sdks-docker)) but code lives only on GitHub or your disk. You need a **write** [access token](https://huggingface.co/settings/tokens) (password when Git asks).

**Option A — Clone the Space, copy this repo in, push (works for empty / template Spaces)**

```bash
# 1) Clone YOUR Space (replace user/slug)
git clone https://huggingface.co/spaces/USER/SPACE_SLUG hf-space
cd hf-space

# 2) Remove everything except .git (bash)
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +

# 3) Copy project files from scam-env root (no .git / .venv)
#    Adjust SOURCE to your local path to this folder.
cp -a /path/to/scam-env/. .

# 4) Commit and push
git add -A
git commit -m "Deploy OpenEnv scam-detection server"
git push
```

**Windows (PowerShell)** — same idea: clone `hf-space`, delete all items except `.git`, then mirror-copy from your `scam-env` folder excluding `.git` and `.venv` (e.g. `robocopy D:\Projects\Scaler_Hack\scam-env . /E /XD .git .venv` from inside `hf-space` after clearing files).

**Option B — Add the Space as a second remote** (only if you are comfortable resolving history; often Option A is simpler.)

```bash
cd /path/to/scam-env
git remote add hf https://huggingface.co/spaces/USER/SPACE_SLUG
git push -u hf main
```

If the Space already has commits Git rejects the push, use **Option A** or `git pull hf main --allow-unrelated-histories` then fix conflicts.

After push, the Space rebuilds from the root [`Dockerfile`](Dockerfile). Example Space URL shape: `https://USER-SPACE_SLUG.hf.space` (see your Space **Settings**).

### Verify (organizer-style ping + one step)

From your machine (replace the URL):

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://YOUR-SPACE.hf.space/reset \
  -H "Content-Type: application/json" -d "{}"
```

Expect `200`. Or use the helper (requires `requests`, already in `requirements.txt`):

```bash
python scripts/hf_smoke_check.py https://YOUR-SPACE.hf.space
```

This calls `POST /reset` then `POST /step` with `verify_sender` and prints status codes; exits **0** only if both return **200**.

## Project layout

```
scam-env/
  env/           # ScamEnv, models, rewards
  tasks/         # Task ids and step budgets
  graders/       # Deterministic 0–1 scores
  data/          # scam_dataset.json (regenerate: python scripts/generate_dataset.py)
  baseline/      # Rule-based agent
  inference.py
  openenv.yaml
  Dockerfile
```

## Custom agent

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from env.scam_env import ScamEnv

env = ScamEnv(task_id="medium", max_steps=12)
obs, info = env.reset(seed=0)
done = False
while not done:
    action = your_policy(obs)
    obs, reward, done, step_info = env.step(action)
```

Then grade with `grade_episode(env.task_id, env.action_trace, info["scenario_id"])`.

## Glossary

| Term | Role |
|------|------|
| **OpenEnv-style API** | `reset` + `step` + observation dict; compatible with standard RL loops. |
| **Observation** | Everything the agent may condition on; keeps evaluation fair. |
| **Step reward** | Shaped feedback for training algorithms. |
| **Grader score** | Single deterministic success metric per hackathon task. |
| **Episode** | One scenario from `reset` until a terminal action or horizon. |

## License

Hackathon / educational use unless otherwise specified.
