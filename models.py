from pydantic import BaseModel, Field


class Action(BaseModel):
    command: str = Field(..., max_length=1000)
    explanation: str = Field(default="", max_length=2000)


class Observation(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    step_number: int = 0
    done: bool = False


class Reward(BaseModel):
    value: float = 0.0
    reason: str = ""


class StepResponse(BaseModel):
    observation: Observation
    reward: Reward
    done: bool


class ResetResponse(BaseModel):
    stdout: str


class SystemState(BaseModel):
    task_id: str
    step_count: int = 0
    max_steps: int = 15
    done: bool = False

    # Task 1: Nginx
    nginx_status: str = "inactive"

    # Task 2: Port conflict
    zombie_pid_alive: bool = True
    port_8080_free: bool = False

    # Task 3: Disk + DB
    disk_usage_percent: int = 100
    large_log_exists: bool = True
    db_status: str = "crashed"

    # Tracking
    diagnostic_commands_run: list[str] = Field(default_factory=list)
    completion_rewarded: bool = False
    diagnostic_rewarded: bool = False
    partial_rewarded: bool = False
