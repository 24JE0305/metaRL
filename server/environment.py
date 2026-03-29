import uuid
from typing import Optional, Dict, Any
from openenv.core.env_server import Environment
from models import CloudAction, CloudObservation, CloudState

GLOBAL_LAST_SCORE = 0.0

class CloudOptimizerEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._current_episode_id: Optional[str] = None

    def _session(self) -> Dict[str, Any]:
        return self._sessions.get(self._current_episode_id, {})

    @property
    def state(self) -> CloudState:
        s = self._session()
        return s.get("state", CloudState())

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        difficulty: str = "easy",
        **kwargs
    ) -> CloudObservation:
        eid = episode_id or str(uuid.uuid4())
        self._current_episode_id = eid

        state = CloudState(
            episode_id=eid,
            step_count=0,
            difficulty=difficulty
        )

        if difficulty == "easy":
            servers = [
                {"server_id": "web-01", "cpu": 80, "ram": "large",  "cost": 10.0},
                {"server_id": "web-02", "cpu": 0,  "ram": "large",  "cost": 10.0},
            ]
            budget = 15.0
            message = "EASY TASK: Terminate 0% CPU server to get under the $15.00/hr budget."

        elif difficulty == "medium":
            servers = [
                {"server_id": "db-01",  "cpu": 10, "ram": "large",  "cost": 10.0},
                {"server_id": "web-01", "cpu": 85, "ram": "medium", "cost": 5.0},
            ]
            budget = 8.0
            message = "MEDIUM TASK: Resize db-01 to 'small' to meet the $8.00/hr budget."

        else:  # hard
            servers = [
                {"server_id": "web-01", "cpu": 90, "ram": "medium", "cost": 5.0},
                {"server_id": "web-02", "cpu": 5,  "ram": "large",  "cost": 10.0},
                {"server_id": "db-01",  "cpu": 0,  "ram": "small",  "cost": 2.0},
            ]
            budget = 10.0
            message = "HARD TASK: Terminate unused server, resize 5% CPU server. Do NOT touch web-01."

        hourly_cost = sum(s["cost"] for s in servers)
        state.starting_cost = hourly_cost
        state.current_cost = hourly_cost

        self._sessions[eid] = {
            "state": state,
            "servers": servers,
            "budget": budget,
            "hourly_cost": hourly_cost,
            "step_count": 0,
            "step_limit": 10,
        }

        return self._make_observation(eid, message)

    def step(
        self,
        action: CloudAction,
        timeout_s: Optional[float] = None,
        episode_id: Optional[str] = None,
        **kwargs
    ) -> CloudObservation:
        global GLOBAL_LAST_SCORE
        if episode_id:
            self._current_episode_id = episode_id

        sess = self._session()
        if not sess:
            return CloudObservation(
                done=True, reward=0.0,
                system_message="No active session.",
                active_servers=[], current_hourly_cost=0.0,
                budget_limit=0.0, website_status="Offline"
            )

        state: CloudState = sess["state"]
        servers = sess["servers"]
        sess["step_count"] += 1
        state.step_count += 1

        reward = 0.0
        message = f"Executed: {action.command}."

        if action.command == "terminate" and action.server_id:
            server = next((s for s in servers if s["server_id"] == action.server_id), None)
            if server:
                if server["cpu"] > 50:
                    state.website_crashed = True
                    message = "CRITICAL: Terminated high-CPU server. Website OFFLINE."
                    reward = -0.5
                else:
                    servers.remove(server)
                    message = f"Terminated {action.server_id}."
                    reward = 0.2
            else:
                message = f"Error: server '{action.server_id}' not found."

        elif action.command == "resize" and action.server_id and action.new_size:
            server = next((s for s in servers if s["server_id"] == action.server_id), None)
            if server:
                server["ram"] = action.new_size
                server["cost"] = {"small": 2.0, "medium": 5.0, "large": 10.0}.get(action.new_size, server["cost"])
                message = f"Resized {action.server_id} to {action.new_size}."
                reward = 0.2
            else:
                message = f"Error: server '{action.server_id}' not found."

        sess["hourly_cost"] = sum(s["cost"] for s in servers)
        state.current_cost = sess["hourly_cost"]

        # Safely check episode completion using the correct variables
        done = (sess["step_count"] >= sess["step_limit"] or state.website_crashed)

        if sess["hourly_cost"] <= sess["budget"] and not state.website_crashed:
            state.target_achieved = True
            done = True
            reward += 0.5 

        # Update the global scoreboard for the /grader endpoint
        if done:
            GLOBAL_LAST_SCORE = 1.0 if state.target_achieved else 0.0

        obs = self._make_observation(self._current_episode_id, message)
        obs.done = done
        obs.reward = reward
        return obs

    def _make_observation(self, eid: str, message: str) -> CloudObservation:
        sess = self._sessions.get(eid, {})
        state = sess.get("state", CloudState())
        return CloudObservation(
            done=False,
            reward=0.0,
            system_message=message,
            active_servers=list(sess.get("servers", [])),
            current_hourly_cost=sess.get("hourly_cost", 0.0),
            budget_limit=sess.get("budget", 0.0),
            website_status="Offline" if state.website_crashed else "Online"
        )