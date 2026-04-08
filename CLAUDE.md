# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NetArena is an SRE (Site Reliability Engineering) Incident Response Simulator built for the OpenEnv / Meta PyTorch Hackathon. An AI agent operates in a **simulated** Linux terminal to diagnose and fix 3 production outages of escalating difficulty.

**Critical design decision**: No real Linux commands run. The environment is a Python dictionary-based state machine that simulates command outputs (systemctl, kill, df, rm, etc.).

## Architecture

```
inference.py (LLM client) → main.py (FastAPI on port 7860) → environment.py (state machine) → graders.py (scoring)
```

- `inference.py` calls the LLM, extracts JSON commands, POSTs to the FastAPI environment, feeds observations back to the LLM
- `main.py` exposes `/reset`, `/step`, `/state`, `/health` endpoints
- `environment.py` contains `SREEnvironment` — a state machine tracking system state per task, with `_dispatch()` handling string-based shell commands
- `graders.py` returns deterministic rewards (0.0–1.0) based on final `SystemState`
- `models.py` defines Pydantic models: `Action`, `Observation`, `Reward`, `SystemState`
- `prompts.py` contains the SRE system prompt enforcing JSON-only output with Chain-of-Thought
- `openenv.yaml` declares task metadata (IDs, difficulty, observation space) for the competition

## The 3-Task SRE Ladder

| Task | Difficulty | Scenario | Success Condition |
|------|-----------|----------|-------------------|
| task1 | Easy | Nginx is down (`inactive`) | Nginx status → `running` |
| task2 | Medium | Port 8080 blocked by zombie process | Zombie PID killed, port clean |
| task3 | Hard | Disk 100% full + database crashed | Disk freed + DB running |

## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the FastAPI environment server
uvicorn main:app --host 0.0.0.0 --port 7860

# Run the inference agent (requires env vars)
API_BASE_URL=http://localhost:7860 MODEL_NAME=<model> HF_TOKEN=<token> python inference.py
```

**Docker** (for Hugging Face Spaces deployment):
```bash
docker build -t netarena .
docker run -p 7860:7860 netarena
```

## OpenEnv Logging Format

`inference.py` must print structured JSON lines to stdout — this is how judges grade:
- `[START]` — emitted on task begin
- `[STEP]` — emitted per action with command, observation, reward
- `[ERROR]` — on exceptions
- `[END]` — final summary with total_reward and status

## Key Constraints

- Max 15 steps per task (OpenEnv standard)
- LLM responses must be JSON: `{"command": "...", "explanation": "..."}`
- `clean_json_output()` in inference.py handles markdown-wrapped or malformed LLM JSON via regex fallback
- FastAPI server targets port 7860 (Hugging Face Spaces requirement)
- Python 3.11-slim base for Docker
