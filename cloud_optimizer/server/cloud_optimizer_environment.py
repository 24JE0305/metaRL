import uuid
from typing import Optional, Any
from openenv.core.env_server import Environment
from models import CloudAction, CloudObservation, CloudState

class CloudOptimizerEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._state = CloudState()
        self._servers = []
        self._budget = 0.0
        self._hourly_cost = 0.0
        self._step_limit = 10
        self._current_step = 0

    def reset(self, seed: Optional[int] = None, episode_id: Optional[str] = None, difficulty: str = "easy", **kwargs) -> CloudObservation:
        """Starts a new episode and generates the servers based on difficulty."""
        self._state = CloudState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            difficulty=difficulty
        )
        self._current_step = 0
        self._servers = []

        # TASK 1: EASY (Terminate the unused server)
        if difficulty == "easy":
            self._servers = [
                {"server_id": "web-01", "cpu": 80, "ram": "large", "cost": 10.0},
                {"server_id": "web-02", "cpu": 0, "ram": "large", "cost": 10.0} # Target to terminate
            ]
            self._budget = 15.0
            message = "EASY TASK: Terminate any server with 0% CPU to get under the $15.00 budget."

        # TASK 2: MEDIUM (Resize oversized servers)
        elif difficulty == "medium":
            self._servers = [
                {"server_id": "db-01", "cpu": 10, "ram": "large", "cost": 10.0}, # Target to resize to small
                {"server_id": "web-01", "cpu": 85, "ram": "medium", "cost": 5.0}
            ]
            self._budget = 8.0
            message = "MEDIUM TASK: Resize the underutilized database server to 'small' ($2.0 cost) to meet the $8.00 budget."

        # TASK 3: HARD (Complex balancing)
        else:
            self._servers = [
                {"server_id": "web-01", "cpu": 90, "ram": "medium", "cost": 5.0},
                {"server_id": "web-02", "cpu": 5, "ram": "large", "cost": 10.0}, # Needs resize
                {"server_id": "db-01", "cpu": 0, "ram": "small", "cost": 2.0}    # Needs termination
            ]
            self._budget = 10.0
            message = "HARD TASK: Terminate unused servers and resize oversized ones to meet the $10.00 budget. Do not crash the website by terminating high-CPU servers."

        self._update_costs()
        self._state.starting_cost = self._hourly_cost

        return self._make_observation(message)

    def step(self, action: CloudAction, timeout_s: Optional[float] = None, **kwargs) -> CloudObservation:
        """Processes the AI's action and calculates partial rewards."""
        self._state.step_count += 1
        self._current_step += 1
        reward = 0.0
        message = f"Executed {action.command}."

        # Handle Action: TERMINATE
        if action.command == "terminate" and action.server_id:
            server = next((s for s in self._servers if s["server_id"] == action.server_id), None)
            if server:
                if server["cpu"] > 50:
                    self._state.website_crashed = True
                    message = f"CRITICAL ERROR: You terminated {action.server_id} which had high CPU. Website crashed!"
                    reward = -0.5 # Penalty for destructive action
                else:
                    self._servers.remove(server)
                    message = f"Successfully terminated {action.server_id}."
                    reward = 0.2 # Partial progress reward
            else:
                message = "Error: Server ID not found."
                reward = -0.1

        # Handle Action: RESIZE
        elif action.command == "resize" and action.server_id and action.new_size:
            server = next((s for s in self._servers if s["server_id"] == action.server_id), None)
            if server:
                server["ram"] = action.new_size
                server["cost"] = 2.0 if action.new_size == "small" else (5.0 if action.new_size == "medium" else 10.0)
                message = f"Resized {action.server_id} to {action.new_size}."
                reward = 0.2 # Partial progress reward
            else:
                message = "Error: Server ID not found."
                reward = -0.1

        self._update_costs()

        # Episode Boundary Logic
        done = self._current_step >= self._step_limit or self._state.website_crashed
        if self._hourly_cost <= self._budget and not self._state.website_crashed:
            self._state.target_achieved = True
            done = True
            reward += 0.5 # Final completion reward

        obs = self._make_observation(message)
        obs.done = done
        obs.reward = reward
        return obs

    @property
    def state(self) -> CloudState:
        return self._state

    def _update_costs(self):
        self._hourly_cost = sum(s["cost"] for s in self._servers)
        self._state.current_cost = self._hourly_cost

    def _make_observation(self, message: str) -> CloudObservation:
        return CloudObservation(
            done=False,
            reward=0.0,
            system_message=message,
            active_servers=self._servers,
            current_hourly_cost=self._hourly_cost,
            budget_limit=self._budget,
            website_status="Offline" if self._state.website_crashed else "Online"
        )