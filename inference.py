import os
import json
from openai import OpenAI
from models import CloudAction
from client import CloudOptimizerClient

def run_inference():
    # Load required hackathon environment variables
    api_key = os.environ.get("HF_TOKEN")
    base_url = os.environ.get("API_BASE_URL")
    model_name = os.environ.get("MODEL_NAME")

    if not api_key or not base_url or not model_name:
        print("Error: HF_TOKEN, API_BASE_URL, or MODEL_NAME environment variables not set.")
        return

    # Instantiate the client using the hackathon API
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    env = CloudOptimizerClient(base_url=os.getenv("ENV_BASE_URL", "http://localhost:8000"))
    
    difficulties = ["easy", "medium", "hard"]
    
    for diff in difficulties:
        print(f"=======================================")
        print(f" STARTING TASK: {diff.upper()}")
        print(f"=======================================")
        
        obs = env.reset(difficulty=diff)
        done = False
        
        while not done:
            prompt = f"""
            Your goal is to reduce costs to meet the budget without crashing the website.
            
            Current Status:
            - Message: {obs.system_message}
            - Hourly Cost: ${obs.current_hourly_cost}
            - Budget Limit: ${obs.budget_limit}
            - Website Status: {obs.website_status}
            
            Active Servers:
            {json.dumps(obs.active_servers, indent=2)}
            
            Available Commands:
            1. "terminate" (requires server_id) - Drops cost to 0. Do not terminate if CPU > 50%.
            2. "resize" (requires server_id, new_size: "small", "medium", "large") - Changes capacity and cost.
            3. "wait" - Do nothing.
            
            Based on the Active Servers and Budget, what is your next action?
            """
            
            # Use the model name passed from the environment
            response = client.beta.chat.completions.parse(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert Cloud FinOps AI agent."},
                    {"role": "user", "content": prompt}
                ],
                response_format=CloudAction, 
            )
            
            action = response.choices[0].message.parsed
            
            print(f"[AGENT] Action: {action.command.upper()} | Server: {action.server_id} | Size: {action.new_size}")
            
            result = env.step(action)
            obs = result.observation
            done = result.done
            
            print(f"[ENV]   Response: {obs.system_message}")
            print(f"        Current Cost: ${obs.current_hourly_cost}\n")
            
        score = 1.0 if env.state.target_achieved else 0.0
        print(f"--- Task '{diff}' Complete ---")
        print(f"Final Cost: ${obs.current_hourly_cost} / Budget: ${obs.budget_limit}")
        print(f"Website Crashed: {env.state.website_crashed}")
        
        print(f"*** GRADER SCORE: {score} ***\n\n")

if __name__ == "__main__":
    run_inference()