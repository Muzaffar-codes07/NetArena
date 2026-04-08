import os
import sys
import json
import requests
import re
from openai import OpenAI
from prompts import SYSTEM_PROMPT

# 1. AUTH & CONFIG (Standard OpenEnv Env Vars)
API_BASE_URL = os.environ.get('API_BASE_URL')
MODEL_NAME = os.environ.get('MODEL_NAME')
HF_TOKEN = os.environ.get('HF_TOKEN')

# Defensive check: bail early if env vars are missing
_missing = [name for name, val in [("API_BASE_URL", API_BASE_URL), ("MODEL_NAME", MODEL_NAME), ("HF_TOKEN", HF_TOKEN)] if not val]
if _missing:
    print(f"ERROR: Missing required environment variables: {', '.join(_missing)}")
    sys.exit(1)

API_BASE_URL = API_BASE_URL.rstrip('/')

# Initialize OpenAI-compatible client pointing to your HF Space
client = OpenAI(base_url=f"{API_BASE_URL}/v1", api_key=HF_TOKEN)

def clean_json_output(raw_output):
    """
    BEAT THE OTHER AIs: This function handles cases where the model
    wraps JSON in markdown code blocks or adds conversational filler.
    """
    try:
        # Attempt direct parse
        return json.loads(raw_output)
    except json.JSONDecodeError:
        # Use Regex to find content between { and } if model added text around it
        match = re.search(r'(\{.*\}|\[.*\])', raw_output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
    # Final fallback if the model completely fails to provide JSON
    return {"command": "ls", "explanation": "Fallback: Model output was not valid JSON."}

def run_task(task_id):
    # --- MANDATORY [START] LOG ---
    print(json.dumps({"event": "[START]", "task": task_id}))

    # Reset Environment with specific task_id
    try:
        resp = requests.post(f"{API_BASE_URL}/reset", params={"task_id": task_id}, timeout=10)
        obs = resp.json()
    except Exception as e:
        print(f"FAILED TO CONNECT TO ENV: {e}")
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"INITIAL ALERT: {obs['stdout']}"}
    ]

    total_reward = 0.0
    step = 0

    # OpenEnv Standard: Max 15 steps
    for step in range(1, 16):
        try:
            # Call LLM with JSON mode enabled, with fallback for providers that don't support it
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
            except Exception:
                # Retry without response_format if the provider doesn't support JSON mode
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=0.2
                )

            raw_content = response.choices[0].message.content
            action = clean_json_output(raw_content)

            # Step the Environment
            step_result = requests.post(
                f"{API_BASE_URL}/step",
                json=action,
                params={"task_id": task_id},
                timeout=10
            ).json()

            observation = step_result['observation']
            reward = step_result['reward']
            done = step_result['done']
            total_reward += reward['value']

            # --- MANDATORY [STEP] LOG (The Grader's Bread and Butter) ---
            print(json.dumps({
                "event": "[STEP]",
                "task": task_id,
                "step": step,
                "command": action.get("command", "none"),
                "explanation": action.get("explanation", "none"),
                "stdout": observation.get('stdout', ''),
                "stderr": observation.get('stderr', ''),
                "exit_code": observation.get('exit_code', 0),
                "reward": reward.get('value', 0.0),
                "reason": reward.get('reason', 'no reason provided')
            }))

            if done:
                break

            # Add to history for context-aware troubleshooting
            messages.append({"role": "assistant", "content": raw_content})
            # If stdout is empty, give the agent the stderr so it knows it failed
            feedback = observation['stdout'] if observation['stdout'] else f"Error: {observation['stderr']}"
            messages.append({"role": "user", "content": feedback})

        except Exception as e:
            # Critical step: don't let the loop crash, log the error and try to continue
            print(json.dumps({"event": "[ERROR]", "task": task_id, "error": str(e)}))
            break

    # --- MANDATORY [END] LOG ---
    print(json.dumps({
        "event": "[END]",
        "task": task_id,
        "total_reward": round(total_reward, 4),
        "total_steps": step,
        "status": "SUCCESS" if total_reward > 0.7 else "PARTIAL"
    }))

if __name__ == "__main__":
    # Ensure the environment is up before starting
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            for task in ["task1", "task2", "task3"]:
                run_task(task)
    except:
        print("CRITICAL: Environment is not reachable. Check API_BASE_URL.")
