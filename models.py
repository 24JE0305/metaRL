from typing import List, Optional, Dict, Any
from openenv.core.env_server import Action, Observation, State                          ## OpenEV as Blue-Print

# -------------------------------- Action -------------------------------- #

class CloudAction(Action):
    """
        AI 'abilities'
    """
    command: str                                                                        ## {"terminate","resize","wait"}
    server_id: Optional[str] = None                                                     ## {"server name"}
    new_size: Optional[str] = None                                                      ## {"small" = $2/hr, "medium" = $5/hr, "large" = $10/hr}

# ------------------------------ Observation ------------------------------ #

class CloudObservation(Observation):
    """
        What the AI sees after taking an action.
    """
    system_message: str
    active_servers: List[Dict[str, Any]]                                                ## {"server_id","CPU(%)","RAM","Cost"}
    current_hourly_cost: float
    budget_limit: float
    website_status: str                                                                 ## {"Online" or "Offline"}

# --------------------------------- State --------------------------------- #

class CloudState(State):
    """
        Hidden state to track the episode for the Grader.
    """
    difficulty: str = "easy"
    starting_cost: float = 0.0
    current_cost: float = 0.0
    website_crashed: bool = False
    target_achieved: bool = False 