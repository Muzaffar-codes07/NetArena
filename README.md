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

An AI agent operates in a **simulated Linux terminal** to diagnose and fix 3 production outages of escalating difficulty. Built for the OpenEnv / Meta PyTorch Hackathon.

## Architecture

```
inference.py (LLM client) → main.py (FastAPI) → environment.py (state machine) → graders.py (scoring)
```

No real Linux commands run. The environment is a Python dictionary-based state machine that simulates command outputs (`systemctl`, `kill`, `df`, `rm`, etc.).

## The 3-Task SRE Ladder

| Task | Difficulty | Scenario | Success Condition |
|------|-----------|----------|-------------------|
| task1 | Easy | Nginx is down | Nginx status → running |
| task2 | Medium | Port 8080 blocked by zombie process | Zombie killed, port free |
| task3 | Hard | Disk 100% full + DB crashed | Disk freed + DB running |

## Quick Start

```bash
pip install -r requirements.txt

# Start the environment server
uvicorn main:app --host 0.0.0.0 --port 7860

# Run the AI agent (separate terminal)
API_BASE_URL=http://localhost:7860 MODEL_NAME=<model> HF_TOKEN=<token> python inference.py
```

## Docker

```bash
docker build -t netarena .
docker run -p 7860:7860 netarena
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/reset?task_id=task1` | POST | Reset environment for a task |
| `/step?task_id=task1` | POST | Execute a command (JSON body: `{"command": "...", "explanation": "..."}`) |
| `/state?task_id=task1` | GET | Get current task state |
