import os
import json
from typing import List, Optional
from openai import OpenAI
from models import CloudAction
from client import CloudOptimizerClient

BENCHMARK    = "cloud_optimizer"
MAX_STEPS    = 10
DIFFICULTIES = ["easy", "medium", "hard"]

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )

def get_action(client: OpenAI, obs, model_name: str) -> CloudAction:
    prompt = f"""You are an expert Cloud FinOps AI agent. Your goal is to reduce 
costs to meet the budget without crashing the website.

Current Status:
- Message: {obs.system_message}
- Hourly Cost: ${obs.current_hourly_cost}
- Budget Limit: ${obs.budget_limit}
- Website Status: {obs.website_status}

Active Servers:
{json.dumps(obs.active_servers, indent=2)}

Available Commands:
1. "terminate" (requires server_id) - Drops cost to $0. Do NOT terminate if CPU > 50%.
2. "resize" (requires server_id, new_size: "small"=$2/hr, "medium"=$5/hr, "large"=$10/hr)
3. "wait" - Do nothing this step.

Respond with a structured CloudAction JSON only."""

    response = client.beta.chat.completions.parse(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are an expert Cloud FinOps AI agent."},
            {"role": "user",   "content": prompt},
        ],
        response_format=CloudAction,
    )
    return response.choices[0].message.parsed


def run_task(client: OpenAI, env: CloudOptimizerClient, difficulty: str, model_name: str):
    task_name = f"cloud_optimizer_{difficulty}"
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=model_name)

    try:
        obs = env.reset(difficulty=difficulty)
        done = False

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            error_msg = None
            try:
                action = get_action(client, obs, model_name)
            except Exception as exc:
                error_msg = str(exc)
                action = CloudAction(command="wait")

            action_str = (
                f"{action.command}"
                + (f"('{action.server_id}')" if action.server_id else "()")
            )

            try:
                result = env.step(action)
                obs    = result.observation
                reward = float(result.reward or 0.0)
                done   = result.done
            except Exception as exc:
                reward    = 0.0
                done      = True
                error_msg = str(exc)

            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=error_msg,
            )

        try:
            score = 1.0 if env.state.target_achieved else 0.0
        except Exception:
            score = 1.0 if rewards and rewards[-1] > 0 else 0.0

        success = score >= 0.5

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


def run_inference():
    # Read env vars INSIDE function so Meta's injected values are always used
    api_key      = os.environ.get("API_KEY") or os.environ.get("HF_TOKEN")
    base_url     = os.environ.get("API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    model_name   = os.environ.get("MODEL_NAME", "gemini-2.5-flash")
    env_base_url = os.environ.get("ENV_BASE_URL", "http://localhost:8000")

    if not api_key:
        print("Error: API_KEY environment variable not set.", flush=True)
        return

    client = OpenAI(api_key=api_key, base_url=base_url)
    env    = CloudOptimizerClient(base_url=env_base_url)

    total_score = 0.0
    for difficulty in DIFFICULTIES:
        score = run_task(client, env, difficulty, model_name)
        total_score += score

    overall = total_score / len(DIFFICULTIES)
    print(f"\nOverall score: {overall:.3f}", flush=True)


if __name__ == "__main__":
    run_inference()