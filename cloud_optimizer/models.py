from typing import List, Optional, Dict, Any
from openenv.core.env_server import Action, Observation, State

class CloudAction(Action):
    """What the AI agent can do."""
    command: str # e.g., "terminate", "resize", "wait"
    server_id: Optional[str] = None
    new_size: Optional[str] = None # e.g., "small", "medium", "large"

class CloudObservation(Observation):
    """What the AI sees after taking an action."""
    system_message: str
    active_servers: List[Dict[str, Any]] # List of servers with their CPU/RAM/Cost
    current_hourly_cost: float
    budget_limit: float
    website_status: str # "Online" or "Offline"

class CloudState(State):
    """Hidden state to track the episode for the Grader."""
    difficulty: str = "easy"
    starting_cost: float = 0.0
    current_cost: float = 0.0
    website_crashed: bool = False