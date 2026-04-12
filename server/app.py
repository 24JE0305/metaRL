import os
import json
import subprocess
from fastapi import Request
from openenv.core.env_server import create_fastapi_app
from models import CloudAction, CloudObservation
from .environment import CloudOptimizerEnvironment
import server.environment as env_module

app = create_fastapi_app(CloudOptimizerEnvironment, CloudAction, CloudObservation)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.api_route("/reset", methods=["GET", "POST"])
async def reset(request: Request):
    body = {}
    try:
        body = await request.json()
    except:
        pass
    difficulty = body.get("difficulty", "easy")
    env = CloudOptimizerEnvironment()
    obs = env.reset(difficulty=difficulty)
    return {
        "observation": obs.model_dump(),
        "reward": 0.0,
        "done": False
    }

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
            
        # FIX: Ensure score is STRICTLY between 0.0 and 1.0
        if env.state.website_crashed:
            score = 0.01
        elif env.state.target_achieved:
            score = 0.99
        else:
            # Partial credit if they reduced cost but didn't hit the target
            start_c = env.state.starting_cost
            curr_c = env.state.current_cost
            target_c = obs.budget_limit
            if start_c > target_c:
                progress = (start_c - curr_c) / (start_c - target_c)
                score = 0.1 + (0.8 * max(0.0, min(1.0, progress))) # Scales between 0.1 and 0.9
            else:
                score = 0.5
                
        results[difficulty] = {
            "score": round(score, 4),
            "final_cost": env.state.current_cost,
            "budget": obs.budget_limit,
            "website_crashed": env.state.website_crashed,
            "target_achieved": env.state.target_achieved
        }
    overall = sum(r["score"] for r in results.values()) / 3
    return {"overall_score": round(overall, 4), "tasks": results}

@app.get("/state")
async def get_state():
    env = CloudOptimizerEnvironment()
    return env.state.model_dump()

@app.get("/baseline")
async def run_baseline():
    try:
        result = subprocess.run(
            ["python", "inference.py"],  
            capture_output=True,
            text=True,
            env=os.environ,          
            timeout=120
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Inference script timed out after 120s"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _rule_based_agent(obs, difficulty: str):
    from models import CloudAction
    servers = obs.active_servers
    for s in servers:
        if s["cpu"] == 0:
            return CloudAction(command="terminate", server_id=s["server_id"])
    for s in servers:
        if s["cpu"] <= 15 and s["ram"] == "large":
            return CloudAction(command="resize", server_id=s["server_id"], new_size="small")
    for s in servers:
        if s["cpu"] <= 20 and s["ram"] == "medium":
            return CloudAction(command="resize", server_id=s["server_id"], new_size="small")
    return CloudAction(command="wait")

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()