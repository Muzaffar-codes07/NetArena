from fastapi import FastAPI, Query, HTTPException
from models import Action, StepResponse, ResetResponse, Observation, Reward
from environment import SREEnvironment
from graders import grade_task

app = FastAPI(title="NetArena — SRE Incident Response Simulator")
env = SREEnvironment()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset(task_id: str = Query(..., description="Task ID (task1, task2, task3)")):
    alert = env.reset(task_id)
    return ResetResponse(stdout=alert)


@app.post("/step")
def step(action: Action, task_id: str = Query(..., description="Task ID")):
    if task_id not in env.tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not initialized. Call /reset first.")

    observation, done = env.step(task_id, action.command)
    reward = grade_task(task_id, env.tasks[task_id])

    return StepResponse(observation=observation, reward=reward, done=done)


@app.get("/state")
def get_state(task_id: str = Query(..., description="Task ID")):
    if task_id not in env.tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not initialized.")
    return env.tasks[task_id]
