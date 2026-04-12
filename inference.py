import os
import json
import asyncio
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
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}",
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

Respond ONLY with a valid JSON object matching exactly this schema (no markdown, no extra text):
{{
  "command": "terminate|resize|wait",
  "server_id": "string or null",
  "new_size": "small|medium|large or null"
}}"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are an expert Cloud FinOps AI agent. Output raw JSON only."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        max_tokens=256, 
    )
    
    content = response.choices[0].message.content.strip()
    
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    parsed_data = json.loads(content)
    return CloudAction(**parsed_data)

# ADDED ASYNC
async def run_task(client: OpenAI, env: CloudOptimizerClient, difficulty: str, model_name: str):
    task_name = f"cloud_optimizer_{difficulty}"
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=model_name)

    try:
        # ADDED AWAIT and safe observation extraction
        reset_result = await env.reset(difficulty=difficulty)
        obs = reset_result.observation if hasattr(reset_result, "observation") else reset_result
        done = False

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            error_msg = None
            action = get_action(client, obs, model_name)

            action_str = (
                f"{action.command}"
                + (f"('{action.server_id}')" if action.server_id else "()")
            )

            try:
                # ADDED AWAIT
                result = await env.step(action)
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
        log_end(success=success, steps=steps_taken, rewards=rewards)

    return score

# ADDED ASYNC
async def run_inference():
    if "API_BASE_URL" not in os.environ:
        os.environ["API_BASE_URL"] = "[https://router.huggingface.co/v1](https://router.huggingface.co/v1)"
    if "API_KEY" not in os.environ:
        os.environ["API_KEY"] = os.environ.get("HF_TOKEN", "dummy-token")
        
    model_name = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

    client = OpenAI(
        base_url=os.environ["API_BASE_URL"],
        api_key=os.environ["API_KEY"]
    )
    
    env = CloudOptimizerClient(base_url=os.environ.get("ENV_BASE_URL", "http://localhost:8000"))

    total_score = 0.0
    for difficulty in DIFFICULTIES:
        # ADDED AWAIT
        score = await run_task(client, env, difficulty, model_name)
        total_score += score

    overall = total_score / len(DIFFICULTIES)
    print(f"\nOverall score: {overall:.3f}", flush=True)

if __name__ == "__main__":
    # ADDED ASYNCIO.RUN()
    asyncio.run(run_inference())