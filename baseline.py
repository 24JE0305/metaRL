import os
import json
from openai import OpenAI
from models import CloudAction
from server.environment import CloudOptimizerEnvironment

def run_baseline():
    # The hackathon judge will inject this into the environment variables
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return

    client = OpenAI(api_key=api_key)
    env = CloudOptimizerEnvironment()
    
    difficulties = ["easy", "medium", "hard"]
    
    for diff in difficulties:
        print(f"=======================================")
        print(f" STARTING TASK: {diff.upper()}")
        print(f"=======================================")
        
        obs = env.reset(difficulty=diff)
        done = False
        
        while not done:
            # 1. Build the prompt using the exact observation data
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
            
            # 2. Call OpenAI and force it to use our CloudAction schema
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert Cloud FinOps AI agent."},
                    {"role": "user", "content": prompt}
                ],
                response_format=CloudAction, # OpenAI will automatically parse the output into our Pydantic class!
            )
            
            action = response.choices[0].message.parsed
            print(f"🤖 Agent Action: {action.command.upper()} | Server: {action.server_id} | Size: {action.new_size}")
            
            # 3. Pass the action back into our environment
            obs = env.step(action)
            done = obs.done
            print(f"💻 Env Response: {obs.system_message}")
            print(f"   Current Cost: ${obs.current_hourly_cost}\n")
            
        # 4. Calculate final grader score
        score = 1.0 if env.state.target_achieved else 0.0
        print(f"--- Task '{diff}' Complete ---")
        print(f"Final Cost: ${obs.current_hourly_cost} / Budget: ${obs.budget_limit}")
        print(f"Website Crashed: {env.state.website_crashed}")
        print(f"🏆 GRADER SCORE: {score}\n\n")

if __name__ == "__main__":
    run_baseline()