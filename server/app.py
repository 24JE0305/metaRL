import os
import json
import subprocess
from fastapi import Request
from openenv.core.env_server import create_fastapi_app
from models import CloudAction, CloudObservation
from .environment import CloudOptimizerEnvironment
import server.environment as env_module

app = create_fastapi_app(CloudOptimizerEnvironment, CloudAction, CloudObservation)

# ── /tasks ──────────────────────────────────────────────
@app.get("/tasks")
async def get_tasks():
    return {
        "tasks": [
            {
                "difficulty": "easy",
                "description": "Terminate the ghost server with 0% CPU to get under the $15.00/hr budget.",
                "expected_difficulty": "easy",
                "target_metric": "hourly_cost <= 15.0"
            },
            {
                "difficulty": "medium",
                "description": "Resize the oversized database server (10% CPU, large RAM) to 'small' to meet the $8.00/hr budget.",
                "expected_difficulty": "medium",
                "target_metric": "hourly_cost <= 8.0"
            },
            {
                "difficulty": "hard",
                "description": "Terminate the 0% CPU server AND resize the 5% CPU server without crashing the 90% CPU web server. Meet the $10.00/hr budget.",
                "expected_difficulty": "hard",
                "target_metric": "hourly_cost <= 10.0 AND website_status == Online"
            }
        ],
        "action_schema": CloudAction.model_json_schema()
    }

# ── /grader ──────────────────────────────────────────────
# Stateless GET: runs all 3 tasks with a simple rule-based agent
# and returns reproducible scores. The hackathon validator calls this.
@app.get("/grader")
async def get_grader():
    from .environment import CloudOptimizerEnvironment
    results = {}
    for difficulty in ["easy", "medium", "hard"]:
        env = CloudOptimizerEnvironment()
        obs = env.reset(difficulty=difficulty)
        done = False
        while not done:
            action = _rule_based_agent(obs, difficulty)
            obs = env.step(action)
            done = obs.done
        score = 1.0 if env.state.target_achieved else 0.0
        results[difficulty] = {
            "score": score,
            "final_cost": env.state.current_cost,
            "budget": obs.budget_limit,
            "website_crashed": env.state.website_crashed,
            "target_achieved": env.state.target_achieved
        }
    overall = sum(r["score"] for r in results.values()) / 3
    return {"overall_score": round(overall, 4), "tasks": results}

# ── /state ───────────────────────────────────────────────
# Required by OpenEnv spec: step() / reset() / state()
@app.get("/state")
async def get_state():
    env = CloudOptimizerEnvironment()
    return env.state.model_dump()

# ── /baseline ────────────────────────────────────────────
@app.get("/baseline")
async def run_baseline():
    try:
        result = subprocess.run(
            ["python", "baseline.py"],
            capture_output=True,
            text=True,
            env=os.environ,          # ← CRITICAL: passes OPENAI_API_KEY through
            timeout=120
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Baseline script timed out after 120s"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── internal rule-based agent (used by /grader) ──────────
def _rule_based_agent(obs, difficulty: str):
    from models import CloudAction
    servers = obs.active_servers
    # Find 0% CPU → terminate
    for s in servers:
        if s["cpu"] == 0:
            return CloudAction(command="terminate", server_id=s["server_id"])
    # Find low CPU large server → resize to small
    for s in servers:
        if s["cpu"] <= 15 and s["ram"] == "large":
            return CloudAction(command="resize", server_id=s["server_id"], new_size="small")
    # Find low CPU medium server → resize to small
    for s in servers:
        if s["cpu"] <= 20 and s["ram"] == "medium":
            return CloudAction(command="resize", server_id=s["server_id"], new_size="small")
    return CloudAction(command="wait")