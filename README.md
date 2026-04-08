---
title: NetArena SRE
emoji: 🔧
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# NetArena — SRE Incident Response Simulator

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://www.docker.com/)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Hackathon-FF4500)](https://openenv.dev/)

> **Companies lose an average of $300,000 per hour of unplanned downtime.** NetArena puts an AI agent on-call — testing whether it can diagnose and resolve production outages faster and more reliably than a human SRE. No guesswork, no LLM judges: every score is mathematically determined by a deterministic state machine.

---

## What Is NetArena?

NetArena is a **sandboxed SRE (Site Reliability Engineering) Incident Response Simulator** built for the OpenEnv / Meta PyTorch Hackathon. An AI agent is dropped into a simulated Linux terminal and tasked with resolving 3 production outages of escalating difficulty — from a downed web server to a full disk + crashed database.

**Key properties:**
- **Zero real system calls.** All commands (`systemctl`, `kill`, `df`, `rm`, etc.) are intercepted by a Python dictionary-based state machine — the environment is completely safe and reproducible.
- **Deterministic scoring.** Rewards are computed from final system state, not LLM opinion. Every run is mathematically verifiable.
- **OpenEnv-compliant.** Structured JSON stdout logging (`[START]`, `[STEP]`, `[END]`) makes evaluation fully automated.

---

## System Architecture

```
inference.py          main.py              environment.py        graders.py
(LLM client)    →    (FastAPI :7860)   →   (state machine)   →   (scoring)
```

| Component | Responsibility |
|---|---|
| `inference.py` | Calls the LLM, extracts JSON commands, POSTs to FastAPI, feeds observations back in a loop |
| `main.py` | Exposes REST API (`/reset`, `/step`, `/state`, `/health`) on port 7860 |
| `environment.py` | `SREEnvironment` — tracks per-task `SystemState`, dispatches string commands to handlers |
| `graders.py` | Reads final `SystemState` and returns a deterministic `Reward` (0.0 – 1.0) |
| `models.py` | Pydantic schemas: `Action`, `Observation`, `Reward`, `SystemState` |
| `prompts.py` | System prompt enforcing JSON-only LLM output with Chain-of-Thought |

> **No real Linux commands ever execute.** The `_dispatch()` method in `environment.py` pattern-matches command strings and mutates a Python dictionary — making the environment portable, safe, and perfectly reproducible across any machine.

---

## The SRE Task Ladder

| # | Task ID | Difficulty | Scenario | Success Condition | Max Steps |
|---|---|---|---|---|---|
| 1 | `task1` | Easy | Nginx web server is `inactive` | `nginx_status == "running"` | 15 |
| 2 | `task2` | Medium | Port 8080 blocked by a zombie process | Zombie PID killed + `port_8080_free == true` | 15 |
| 3 | `task3` | Hard | Disk at 100% + PostgreSQL crashed | `disk_usage_percent < 90` + `db_status == "running"` | 15 |

### Task Details

**Task 1 — Service Down (Easy)**
The Nginx web server has stopped. The agent must inspect service status, identify that Nginx is `inactive`, and issue the correct restart command. A single, well-reasoned command chain solves it.

**Task 2 — Port Conflict (Medium)**
Port 8080 is held hostage by a zombie process. The agent must list running processes or check `lsof`/`ss` to find the offending PID, kill it, and confirm the port is clear before the application can rebind.

**Task 3 — Disk Full and DB Crash (Hard)**
The disk is at 100% capacity, which has caused PostgreSQL to crash. The agent must locate the oversized log file (typically several GB), truncate or delete it to free disk space, then restart the database. Both conditions must be resolved for full credit — partial fixes earn partial credit.

---

## Quick Start

### Prerequisites

- Python 3.11+
- An OpenAI-compatible LLM endpoint + API token

### 1. Clone and Install

```bash
git clone https://github.com/Muzaffar-codes07/NetArena.git
cd NetArena
pip install -r requirements.txt
```

### 2. Start the Environment Server

```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

The FastAPI server is now live at `http://localhost:7860`. Swagger docs available at `http://localhost:7860/docs`.

### 3. Run the AI Agent

Set the required environment variables and launch the inference loop:

```bash
export API_BASE_URL=http://localhost:7860
export MODEL_NAME=<your-model-name>          # e.g. meta-llama/Llama-3-8b-instruct
export HF_TOKEN=<your-huggingface-token>

python inference.py
```

The agent will iterate through all 3 tasks, printing structured JSON logs to stdout for each step.

---

## Docker Deployment

```bash
# Build the image
docker build -t netarena .

# Run the container
docker run -p 7860:7860 netarena
```

The container starts the FastAPI server on port 7860 — matching the Hugging Face Spaces `app_port` requirement.

---

## API Reference

All endpoints accept and return JSON.

### `GET /health`
Health check. Returns `{"status": "ok"}`.

---

### `POST /reset?task_id={task_id}`
Initialises a task and returns the opening alert.

**Query params:** `task_id` — one of `task1`, `task2`, `task3`

**Response:**
```json
{
  "stdout": "ALERT: Nginx is not responding. Customers are seeing 502 errors."
}
```

---

### `POST /step?task_id={task_id}`
Executes one agent action. Returns the simulated terminal output, current reward, and done flag.

**Query params:** `task_id` — must match a previously reset task

**Request body:**
```json
{
  "command": "systemctl status nginx",
  "explanation": "Check why Nginx is not responding."
}
```

**Response:**
```json
{
  "observation": {
    "stdout": "● nginx.service - A high performance web server\n   Loaded: loaded\n   Active: inactive (dead)",
    "stderr": "",
    "exit_code": 3,
    "step_number": 1,
    "done": false
  },
  "reward": {
    "value": 0.1,
    "reason": "Diagnostic investigation started."
  },
  "done": false
}
```

---

### `GET /state?task_id={task_id}`
Returns the full internal `SystemState` for a task. Useful for debugging.

---

## Evaluation & Logging

### Scoring Methodology

Rewards are computed deterministically from `SystemState` in `graders.py`:

| Event | Reward | Condition |
|---|---|---|
| Diagnostic started | +0.1 | Any diagnostic command run |
| Partial fix (Task 3 only) | +0.3 | Disk freed **or** DB restarted (not both) |
| Full resolution | +1.0 | All success conditions met |

Rewards are **non-cumulative per grading call** — the grader returns the highest applicable reward at each step to avoid double-counting.

### OpenEnv Logging Standard

`inference.py` emits structured JSON to stdout for automated judging:

```jsonc
// Task begins
{"event": "[START]", "task": "task1"}

// Each action
{"event": "[STEP]", "task": "task1", "step": 1, "command": "systemctl status nginx", "observation": "...", "reward": 0.1}

// On exception
{"event": "[ERROR]", "task": "task1", "error": "Connection refused"}

// Task ends
{"event": "[END]", "task": "task1", "total_reward": 1.1, "status": "success", "steps_taken": 3}
```

---

## Baseline Scores

| Model | Task 1 Score | Task 2 Score | Task 3 Score | Total |
|---|---|---|---|---|
| *(TBD)* | — | — | — | — |
| *(TBD)* | — | — | — | — |
| *(TBD)* | — | — | — | — |

> Fill in before final submission with model name and achieved scores.

---

## Project Structure

```
NetArena/
├── main.py            # FastAPI server — entry point for the environment
├── environment.py     # SREEnvironment state machine + command dispatcher
├── graders.py         # Deterministic reward functions per task
├── inference.py       # LLM agent loop + OpenEnv-compliant logging
├── models.py          # Pydantic data models
├── prompts.py         # System prompt (JSON-only, Chain-of-Thought)
├── openenv.yaml       # Task metadata for the OpenEnv competition
├── requirements.txt   # Python dependencies
└── Dockerfile         # Container definition for HF Spaces deployment
```

---

## Built For

**OpenEnv / Meta PyTorch Hackathon** — a competition to build robust, evaluatable AI agent environments with deterministic, bias-free scoring.
