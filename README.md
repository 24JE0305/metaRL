---
title: Cloud Optimizer FinOps
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
tags:
  - openenv
---

# OpenEnv: Autonomous Cloud Cost Optimizer (FinOps)

## Environment Description & Motivation

**The Problem:** Companies waste an estimated 30% of their cloud infrastructure
budget on unused or oversized servers — billions of dollars annually.

**The Solution:** This OpenEnv environment provides a rigorous sandbox to train
and evaluate AI agents on **Autonomous FinOps**. The agent analyzes simulated
server clusters, calculates costs, and safely executes `terminate` or `resize`
commands to meet a strict budget target without crashing the website.

This is a real-world task: FinOps engineers do exactly this every day in AWS,
GCP, and Azure consoles. Automating it with a reliable AI agent has direct
commercial value.

---

## Action Space (`CloudAction`)

| Field | Type | Required | Values |
|---|---|---|---|
| `command` | str | yes | `"terminate"`, `"resize"`, `"wait"` |
| `server_id` | str | for terminate/resize | e.g. `"web-01"` |
| `new_size` | str | for resize only | `"small"`, `"medium"`, `"large"` |

**Cost by size:** small = $2/hr, medium = $5/hr, large = $10/hr

---

## Observation Space (`CloudObservation`)

| Field | Type | Description |
|---|---|---|
| `system_message` | str | Feedback on the last action taken |
| `active_servers` | List[Dict] | Each server's `server_id`, `cpu` (%), `ram`, `cost` |
| `current_hourly_cost` | float | Total cost per hour across all servers |
| `budget_limit` | float | Target cost the agent must get under |
| `website_status` | str | `"Online"` or `"Offline"` |

---

## Task Descriptions

### Easy — Terminate the ghost server
- **Starting servers:** web-01 (80% CPU, large, $10/hr), web-02 (0% CPU, large, $10/hr)
- **Starting cost:** $20/hr
- **Budget target:** ≤ $15/hr
- **Solution:** Terminate web-02 (0% CPU = safe to remove)
- **Expected difficulty:** Any capable LLM solves this in 1 step

### Medium — Resize the oversized database
- **Starting servers:** db-01 (10% CPU, large, $10/hr), web-01 (85% CPU, medium, $5/hr)
- **Starting cost:** $15/hr
- **Budget target:** ≤ $8/hr
- **Solution:** Resize db-01 to small ($2/hr), bringing total to $7/hr
- **Expected difficulty:** Requires understanding CPU vs cost tradeoff

### Hard — Multi-step optimization without crashing
- **Starting servers:** web-01 (90% CPU, medium, $5/hr), web-02 (5% CPU, large, $10/hr), db-01 (0% CPU, small, $2/hr)
- **Starting cost:** $17/hr
- **Budget target:** ≤ $10/hr
- **Solution:** Terminate db-01 (0% CPU) + resize web-02 to small → total $7/hr. Must NOT touch web-01 (90% CPU = website crash)
- **Expected difficulty:** Requires multi-step planning and risk awareness

---

## Reward Function

| Event | Reward |
|---|---|
| Successful terminate (CPU ≤ 50%) | +0.2 |
| Successful resize | +0.2 |
| Terminating high-CPU server (CPU > 50%) | -0.5 |
| Reaching budget target without crash | +0.5 |

Rewards are given at each step, providing partial progress signal throughout
the episode rather than only at the end.

---

## Setup Instructions

### 1. Clone the repo
```bash
git clone https://github.com/24JE0305/metaRL.git
cd metaRL
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the server locally
```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### 4. Verify it works
```bash
curl http://localhost:8000/health
curl http://localhost:8000/tasks
curl http://localhost:8000/grader
```

### 5. Run with Docker
```bash
docker build -t cloud-optimizer .
docker run -p 8000:8000 cloud-optimizer
```

---

## Running the Inference Script

Set the required environment variables first:
```bash
# Windows PowerShell
$env:HF_TOKEN="your-huggingface-token"
$env:API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
$env:MODEL_NAME="gemini-2.5-flash"
$env:ENV_BASE_URL="http://localhost:8000"

# Linux / Mac
export HF_TOKEN="your-huggingface-token"
export API_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export MODEL_NAME="gemini-2.5-flash"
export ENV_BASE_URL="http://localhost:8000"
```

Then run:
```bash
python inference.py
```

---

## Baseline Scores

Scores from the deterministic rule-based agent (accessible at `/grader`):

| Task | Score | Final Cost | Budget |
|---|---|---|---|
| Easy | 1.0 / 1.0 | $10/hr | $15/hr |
| Medium | 1.0 / 1.0 | $7/hr | $8/hr |
| Hard | 1.0 / 1.0 | $7/hr | $10/hr |
| **Overall** | **1.0 / 1.0** | | |

To reproduce:
```bash
curl http://localhost:8000/grader
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/reset` | POST | Start a new episode |
| `/step` | POST | Take an action |
| `/state` | GET | Get current environment state |
| `/tasks` | GET | List all tasks with descriptions |
| `/grader` | GET | Run deterministic grader, returns scores |
| `/baseline` | GET | Run inference.py and return output |