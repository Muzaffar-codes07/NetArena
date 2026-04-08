from fastapi import FastAPI, Query, HTTPException
from models import Action, StepResponse, ResetResponse, Observation, Reward
from environment import SREEnvironment
from graders import grade_task

app = FastAPI(title="NetArena — SRE Incident Response Simulator")
env = SREEnvironment()

VALID_TASK_IDS = {"task1", "task2", "task3"}


def _validate_task_id(task_id: str) -> None:
    if task_id not in VALID_TASK_IDS:
        raise HTTPException(status_code=400, detail="Invalid task_id. Must be one of: task1, task2, task3")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset(task_id: str = Query(..., description="Task ID (task1, task2, task3)")):
    _validate_task_id(task_id)
    alert = env.reset(task_id)
    return ResetResponse(stdout=alert)


@app.post("/step")
def step(action: Action, task_id: str = Query(..., description="Task ID")):
    _validate_task_id(task_id)
    if task_id not in env.tasks:
        raise HTTPException(status_code=404, detail="Task not initialized. Call /reset first.")

    observation, done = env.step(task_id, action.command)
    reward = grade_task(task_id, env.tasks[task_id])

    return StepResponse(observation=observation, reward=reward, done=done).model_dump()


@app.get("/state")
def get_state(task_id: str = Query(..., description="Task ID")):
    _validate_task_id(task_id)
    if task_id not in env.tasks:
        raise HTTPException(status_code=404, detail="Task not initialized. Call /reset first.")
    return env.tasks[task_id]
