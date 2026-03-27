# ☁️ OpenEnv: Autonomous Cloud Cost Optimizer (FinOps)

## 📖 Environment Description & Motivation
**The Problem:** Companies waste an estimated 30% of their cloud infrastructure budget (billions of dollars annually) on unused or oversized servers. While monitoring tools (like Datadog or AWS CloudWatch) can flag these inefficiencies, it still requires a human DevOps engineer to log in, assess the risk, and manually terminate or resize the instances.

**The Solution:** This OpenEnv simulation provides a rigorous sandbox to train and evaluate AI agents on **Autonomous FinOps**. The agent must analyze simulated server clusters, calculate costs, and safely execute `terminate` or `resize` commands to meet a strict budget *without* crashing the website by removing high-load instances.

## 🧩 Action and Observation Spaces

### Action Space (`CloudAction`)
The agent can take one of three actions per step:
* `command` (str): The action to take (`"terminate"`, `"resize"`, or `"wait"`).
* `server_id` (str, optional): The target server (e.g., `"web-01"`).
* `new_size` (str, optional): Required if resizing (`"small"`, `"medium"`, `"large"`).

### Observation Space (`CloudObservation`)
After each action, the agent observes:
* `system_message` (str): Feedback on the last action.
* `active_servers` (List[Dict]): The current cluster showing CPU usage, RAM size, and hourly cost.
* `current_hourly_cost` (float): The current total burn rate.
* `budget_limit` (float): The target cost the agent must achieve.
* `website_status` (str): `"Online"` or `"Offline"` (if the agent crashes it).

## 🎯 Task Descriptions & Expected Difficulty
The environment initializes with `reset(difficulty="...")` into three distinct scenarios:

1. **Easy (Find the Ghost Server):** * *Scenario:* The cluster contains an expensive server with 0% CPU utilization.
   * *Goal:* Identify and `terminate` the unused server to get under the $15.00 budget.
2. **Medium (Right-Sizing):** * *Scenario:* The cluster contains a database server that is massively oversized for its 10% CPU load.
   * *Goal:* `resize` the database to `"small"` to meet the $8.00 budget.
3. **Hard (High-Stakes Balancing):** * *Scenario:* A complex web of oversized, underutilized, and highly-loaded servers.
   * *Goal:* The agent must terminate the 0% CPU server AND resize the 5% CPU server. If the agent accidentally terminates the 90% CPU web server, the website crashes, resulting in immediate failure.

## 🛠️ Setup and Usage Instructions

**1. Install Dependencies:**
```bash
pip install -r requirements.txt
2. Run the Environment Server Locally:

Bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
3. Test via Python Client:

Python
from client import CloudOptimizerClient
from models import CloudAction

env = CloudOptimizerClient(base_url="http://localhost:8000")
obs = env.reset(difficulty="easy")
result = env.step(CloudAction(command="terminate", server_id="web-02"))
print(result.reward)
📊 Baseline Scores
This repository includes a baseline.py inference script utilizing gpt-4o-mini with OpenAI's Structured Outputs.

To reproduce the baseline:

Bash
export OPENAI_API_KEY="your-api-key"
python baseline.py
Reproduced Grader Scores:

Easy: 1.0 / 1.0 (Target Achieved)

Medium: 1.0 / 1.0 (Target Achieved)

Hard: 1.0 / 1.0 (Target Achieved)


Once you've saved this, make sure your `OPENAI_API_KEY` is set and run `python baseline.py` to see your agent dominate the environment! Let me know if you run into any errors during the test.