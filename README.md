---
title: Cloud Optimizer FinOps
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
---

# OpenEnv: Autonomous Cloud Cost Optimizer (FinOps)

## Environment Description & Motivation
**The Problem:** Companies waste an estimated 30% of their cloud infrastructure budget (billions of dollars annually) on unused or oversized servers. 

**The Solution:** This OpenEnv simulation provides a rigorous sandbox to train and evaluate AI agents on **Autonomous FinOps**. The agent must analyze simulated server clusters, calculate costs, and safely execute `terminate` or `resize` commands to meet a strict budget without crashing the website.

## Action and Observation Spaces

### Action Space (`CloudAction`)
* `command` (str): `"terminate"`, `"resize"`, or `"wait"`.
* `server_id` (str, optional): The target server.
* `new_size` (str, optional): `"small"`, `"medium"`, `"large"`.

### Observation Space (`CloudObservation`)
* `system_message` (str): Feedback on the last action.
* `active_servers` (List[Dict]): CPU usage, RAM, and cost.
* `current_hourly_cost` (float): Current burn rate.
* `budget_limit` (float): The target cost to achieve.
* `website_status` (str): `"Online"` or `"Offline"`.

## Task Descriptions 
1. **Easy:** Terminate the unused 0% CPU server.
2. **Medium:** Resize the oversized database server.
3. **Hard:** Terminate the unused server and resize the low-usage server without crashing the high-usage web server.

## Setup Instructions
**1. Install Dependencies:**
`pip install -r requirements.txt`

**2. Run the Server:**
`uvicorn server.app:app --host 0.0.0.0 --port 8000`

## Baseline Scores
To reproduce the baseline:
`export OPENAI_API_KEY="your-api-key"`
`python baseline.py`

**Scores:**
* Easy: 1.0 / 1.0 
* Medium: 1.0 / 1.0 
* Hard: 1.0 / 1.0