from models import SystemState, Reward


def grade_task(task_id: str, state: SystemState) -> Reward:
    grader = {
        "task1": _grade_task1,
        "task2": _grade_task2,
        "task3": _grade_task3,
    }.get(task_id)

    if grader is None:
        return Reward(value=0.0, reason=f"Unknown task: {task_id}")
    return grader(state)


def _grade_task1(state: SystemState) -> Reward:
    if state.nginx_status == "running" and not state.completion_rewarded:
        state.completion_rewarded = True
        return Reward(value=1.0, reason="Nginx successfully restored to running state.")

    if not state.diagnostic_rewarded and len(state.diagnostic_commands_run) >= 1:
        state.diagnostic_rewarded = True
        return Reward(value=0.1, reason="Diagnostic investigation started.")

    return Reward(value=0.0, reason="Nginx is still down." if state.nginx_status != "running" else "Already rewarded.")


def _grade_task2(state: SystemState) -> Reward:
    both_fixed = not state.zombie_pid_alive and state.port_8080_free
    if both_fixed and not state.completion_rewarded:
        state.completion_rewarded = True
        return Reward(value=1.0, reason="Zombie process killed and port 8080 freed.")

    if not state.diagnostic_rewarded and len(state.diagnostic_commands_run) >= 1:
        state.diagnostic_rewarded = True
        return Reward(value=0.1, reason="Diagnostic investigation started.")

    return Reward(value=0.0, reason="Port 8080 still blocked." if not both_fixed else "Already rewarded.")


def _grade_task3(state: SystemState) -> Reward:
    disk_ok = state.disk_usage_percent < 90
    db_ok = state.db_status == "running"

    if disk_ok and db_ok and not state.completion_rewarded:
        state.completion_rewarded = True
        return Reward(value=1.0, reason="Disk space freed and PostgreSQL database restored.")

    if (disk_ok or db_ok) and not state.completion_rewarded:
        # Partial credit — only given once via completion_rewarded
        if disk_ok and not db_ok:
            return Reward(value=0.3, reason="Disk space freed but database still down.")
        if db_ok and not disk_ok:
            return Reward(value=0.3, reason="Database running but disk still full.")

    if not state.diagnostic_rewarded and len(state.diagnostic_commands_run) >= 1:
        state.diagnostic_rewarded = True
        return Reward(value=0.1, reason="Diagnostic investigation started.")

    return Reward(value=0.0, reason="No progress." if not (disk_ok or db_ok) else "Partial progress.")
