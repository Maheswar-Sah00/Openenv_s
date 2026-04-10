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

# 🛡️ Scam Detection — Fraud Analyst OpenEnv

> _“A message arrives. You have a limited budget of steps. Triage, verify, warn — or miss the scam.”_

**Scam Detection** is an **OpenEnv-compliant** environment where agents act as **bank/fintech fraud analysts**: discrete actions over a structured observation, **step rewards** for RL-style training, and a **deterministic grader** in **[0.0, 1.0]** per episode.

---

## ✅ Phase 2 validation (organizer checks)

These map to the **deep validation** steps in the hackathon dashboard (Docker build → inference → parsing → task logic → LLM/proxy).

| Check | What the judge expects | How this repo satisfies it |
|-------|------------------------|----------------------------|
| **Docker build creation** | Image builds from repo root. | [`Dockerfile`](Dockerfile): Python 3.11-slim, `pip install -r requirements.txt`, `EXPOSE 7860`, `CMD` runs `uvicorn server.app:app` on `${PORT:-7860}`. |
| **`inference.py` execution** | Script runs inside the built image without extra setup. | `docker run --rm <image> python inference.py ...` works; dependencies in [`requirements.txt`](requirements.txt). |
| **Output parsing** | Stdout lines match the required protocol so logs can be scored. | Only **`[START]`**, **`[STEP]`**, **`[END]`** on stdout per episode; **`score=`** with **three** decimal places on `[END]`. See [Output protocol](#output-protocol-judge-parsing) below. |
| **Task validation** | At least **3 tasks** with graders; each task score **strictly in (0, 1)** (not `0.0` / `1.0`). | **Canonical module:** [`tasks/graders.py`](tasks/graders.py) (`grade_action`, `grade_episode`, `_grade_easy` / `_medium` / `_hard`). Core math in [`graders/scam_grader.py`](graders/scam_grader.py). [`openenv.yaml`](openenv.yaml) **`tasks:`** each set `grader: tasks/graders.py` with `id`, `description`, `steps`, `ideal_action`; [`task_graders.json`](task_graders.json) lists the same. Scores **0.01–0.99**. |

**Why “Not enough tasks with graders” appears:** many validators only scan **`tasks/graders.py`** (community layout) or a rich **`tasks:`** list in YAML. Keeping all logic under `graders/scam_grader.py` only, without a **`tasks/graders.py`** entrypoint, fails those heuristics even when behavior is correct.
| **LLM criteria check** | Model calls go through the **injected LiteLLM proxy** (observed API usage). | `inference.py` builds `OpenAI(base_url=os.getenv("API_BASE_URL", ...), api_key=os.getenv("API_KEY") or os.getenv("HF_TOKEN"))`. Default agent is **`llm`** when **`API_KEY`** or **`HF_TOKEN`** is set — **do not** hardcode keys or swap in a private base URL for official eval. |

**Local preflight (mirrors organizer flow):**

```bash
docker build -t scam-detection-env .
docker run --rm scam-detection-env python inference.py --agent baseline --task easy --episodes 1 --seed 42
docker run --rm -p 7860:7860 -e PORT=7860 scam-detection-env
# then: curl -s -o NUL -w "%{http_code}\n" -X POST http://127.0.0.1:7860/reset -H "Content-Type: application/json" -d "{}"
```

---

## 🧠 Why this environment exists

Scams move across **SMS, email, WhatsApp, and in-app** channels. Analysts must:

* **Verify** before trusting urgent messages.
* **Warn** users without crying wolf on legitimate traffic.
* **Escalate or flag** under time pressure when the thread **unfolds over steps** (hard tasks).

This env standardizes that loop for **benchmarking LLMs and RL agents** — same observation schema, same action set, same grader — so scores are comparable across models.

---

## ⚙️ Environment design

### How it works

```
Agent / inference.py              ScamEnv (in-process or via HTTP)
        │                                    │
        │── reset(seed, scenario_id?) ───────▶│  Case loaded from dataset
        │◀─ observation + info ───────────────│  (message, channel, risk hints, …)
        │                                    │
        │── step(action) ───────────────────▶│  State + reward + done
        │◀───────────────────────────────────│  Grader score at episode end
        │         [repeat until terminal      │
        │          or max_steps]             │
```

**HTTP mode (HF Space):** OpenEnv FastAPI exposes **`POST /reset`**, **`POST /step`**, **`GET /state`**, **`/docs`**. The validator pings **`POST /reset`** → **200**.

### Observation space (agent-visible)

Schema version and keys are declared in [`openenv.yaml`](openenv.yaml).

| Field | Meaning |
|--------|---------|
| `case_id` | Stable scenario id (graders reload metadata by id). |
| `message_text` | Latest visible line in the thread. |
| `conversation_history` | All lines revealed so far. |
| `sender_type` | e.g. `unknown`, `bank_official`. |
| `channel` | `sms`, `email`, `whatsapp`, `in_app`. |
| `link_present` | Visible content references a link. |
| `urgency_score` | 0–1 pressure heuristic from scenario data. |
| `sender_verified` | `null` until `verify_sender`; then `true`/`false` vs ground truth. |
| `risk_score` | Analyst-facing score. |
| `risk_factors` | Explainability strings (e.g. `otp_keyword_present`). |
| `steps_taken` / `max_episode_steps` | Horizon. |
| `terminal_actions` | Which actions end the episode. |

**Hidden:** dataset `true_label` and internal stages — rewards/graders only.

### Action space

| Action | Notes |
|--------|--------|
| `ignore` | Terminal — close case. |
| `verify_sender` | Updates `sender_verified`. |
| `warn_user` | Customer warning. |
| `flag_scam` | Terminal. |
| `block_sender` | Terminal. |
| `escalate_to_bank` | Terminal. |

**Reveal rules:** easy = full thread immediately; medium = more lines after `verify_sender` on scams; hard = **one new line per non-terminal step**.

---

## 🎯 Tasks

| Task ID | Difficulty | Core requirement |
|---------|------------|------------------|
| `easy` | 🟢 Easy | Scam → flag / escalate / block; legitimate → no false flag. |
| `medium` | 🟡 Medium | Scams: **`verify_sender`** + **`warn_user`** before full credit; content gated until verify. |
| `hard` | 🔴 Hard | Early verify + warn + terminal escalation/flag; late verify can reduce score. |

**Grader:** entry [`tasks/graders.py`](tasks/graders.py); rules in [`graders/scam_grader.py`](graders/scam_grader.py). **`gray_area`** rows use **partial credit**.

---

## 🏆 Rewards

**Step rewards** ([`env/reward.py`](env/reward.py)) — dense signal for RL; **not** the official competition scalar:

| Signal | Typical range |
|--------|----------------|
| Completed verification | **+0.3** |
| Correct scam terminal | **+1.0** |
| False alarm on legitimate | **−0.5** |
| Missed scam (`ignore`) | **−1.0** |

**Episode score:** grader output in **[0, 1]** on the `[END]` line.

---

## 📋 Output protocol (judge parsing)

**Only these stdout lines**, in order, per episode:

1. `[START] task=<task> env=<benchmark> model=<model_name>`
2. `[STEP] step=<n> action=<action> reward=<0.00> done=<true|false> error=<msg|null>`
3. `[END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...>`

* `score` uses **exactly three** fractional digits; value is **strictly between 0 and 1** (grader clamps to **0.01–0.99**, so e.g. `score=0.990` not `score=1.000`).
* `done` / `success` are lowercase `true` or `false`.
* `error=` is the literal `null` or a single-line message.

Implementation: [`inference.py`](inference.py) (`log_start`, `log_step`, `log_end`).

---

## 📡 API reference (HTTP / OpenEnv)

Interactive docs: **`/docs`** on the running server.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reset` | Start episode (empty body `{}` OK for validator). |
| POST | `/step` | Send action, e.g. `{"action": {"action": "verify_sender", "metadata": {}}}`. |
| GET | `/state` | Current observation / episode metadata (OpenEnv). |
| GET | `/` | Small JSON: `ok`, `env`, `docs` path. |
| GET | `/docs` | Swagger UI. |

---

## 🚀 Quick start

### 1. Installation

```bash
cd scam-env
pip install -r requirements.txt
```

(Optional: `uv sync` if you use `uv` + `pyproject.toml`.)

### 2. Environment variables (LLM / hackathon)

| Variable | Role |
|----------|------|
| `API_BASE_URL` | Injected LiteLLM / OpenAI-compatible base URL. |
| `API_KEY` | Injected proxy key (**preferred**). |
| `HF_TOKEN` | Local Hugging Face router only (fallback). |
| `MODEL_NAME` | Chat model id. |
| `SCAM_ENV_AGENT` | `llm` or `baseline` (default: **llm** if any key is set, else **baseline**). |

### 3. Run the server (local)

```bash
uvicorn server.app:app --host 127.0.0.1 --port 7860
```

### 4. Docker

```bash
docker build -t scam-detection-env .
docker run --rm -p 7860:7860 -e PORT=7860 scam-detection-env
```

### 5. Run `inference.py`

**Baseline (no API key):**

```bash
python inference.py --agent baseline --task easy --episodes 1 --seed 42
python inference.py --agent baseline --all-tasks --seed 42
```

**LLM (example — local HF router):**

```bash
set API_KEY=your_token_here
set API_BASE_URL=https://router.huggingface.co/v1
set MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
python inference.py --agent llm --task easy --episodes 1 --seed 42
```

**Inside the container:**

```bash
docker run --rm scam-detection-env python inference.py --agent baseline --task easy --episodes 1
```

Other useful vars: `SCAM_ENV_MAX_RUNTIME_SEC` (default **1140**), `SUCCESS_SCORE_THRESHOLD`, `SCAM_ENV_LLM_MAX_RETRIES`, `SCAM_ENV_LLM_JSON_MODE`, `SCAM_ENV_DEBUG`.

---

## 🧪 Testing & validation

| Command | Purpose |
|---------|---------|
| `python -m py_compile inference.py` | Syntax check. |
| `python inference.py --agent baseline --all-tasks --seed 42` | End-to-end stdout protocol + grader. |
| `openenv validate` (with `openenv-core[cli]`) | Manifest + layout vs [`openenv.yaml`](openenv.yaml). |
| `python -m unittest tests.test_three_task_graders -v` | `tasks/graders.py` + `openenv.yaml` `tasks:` + `task_graders.json`. |
| `python scripts/verify_task_graders.py` | Quick check that [`task_graders.json`](task_graders.json) files exist. |
| `python scripts/validate_dataset.py` | Dataset schema. |
| `docker build -t scam-detection-env .` | Same as Phase 2 **Docker build**. |
| `python scripts/hf_smoke_check.py https://YOUR-SPACE.hf.space` | `POST /reset` + `POST /step`. |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | CI: install, inference, validate, docker build. |

---

## 📁 Project structure

```
scam-env/
├── openenv.yaml           # OpenEnv manifest (validate / HF)
├── Dockerfile             # Phase 2 container build
├── requirements.txt
├── inference.py           # Benchmark driver + stdout protocol
├── env/                   # ScamEnv, models, step rewards
├── tasks/                 # easy / medium / hard budgets + task ids
├── tasks/graders.py       # Canonical grader API (Phase 2 layout)
├── graders/               # scam_grader (core) + optional easy/medium/hard wrappers
├── task_graders.json      # Machine-readable 3-task grader registry
├── tests/                 # unittest: tasks/graders + manifest
├── data/                  # scam_dataset.json
├── baseline/              # Rule-based agent
├── server/                # FastAPI (create_app) + OpenEnv types
└── scripts/               # dataset, eval export, smoke checks, validate-submission
```

---

## 🌐 Hugging Face Spaces

Frontmatter YAML configures the Space card. Use **Docker** SDK, **port 7860**, repo **root** = this folder (same level as `Dockerfile` and `openenv.yaml`).

1. Create Space → Docker → import from GitHub or `git remote add` + `git push` to `https://huggingface.co/spaces/<user>/<slug>`.
2. After deploy: `https://<user>-<space>.hf.space/docs`.

**Ping check:**

```bash
curl -s -o NUL -w "%{http_code}\n" -X POST https://YOUR-SPACE.hf.space/reset -H "Content-Type: application/json" -d "{}"
```

(Windows PowerShell: `-o $null` instead of `-o NUL`.)

---

## 📎 Dataset & extra tooling

* Regenerate: `python scripts/generate_dataset.py` · Validate: `python scripts/validate_dataset.py`
* Merge external CSV: `python scripts/merge_external_datasets.py --help`
* Human table: `python scripts/human_eval.py --task easy --episodes 5 --seed 42`
* JSONL/CSV: `python scripts/eval_export.py --task easy --episodes 20 --format jsonl -o results.jsonl`
* Shell pre-check: [`scripts/validate-submission.sh`](scripts/validate-submission.sh)

---

## 🧩 Custom agent (in-process)

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

Grade with `from tasks.graders import grade_episode` then `grade_episode(env.task_id, env.action_trace, info["scenario_id"])`.

---

## 📜 License

Hackathon / educational use unless otherwise specified.
