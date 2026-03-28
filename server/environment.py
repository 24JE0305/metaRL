import uuid
from typing import Optional, Dict, Any
from openenv.core.env_server import Environment
from models import CloudAction, CloudObservation, CloudState

GLOBAL_LAST_SCORE = 0.0

class CloudOptimizerEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        # Per-session state keyed by episode_id
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._current_episode_id: Optional[str] = None

    # ── helpers ──────────────────────────────────────────
    def _session(self) -> Dict[str, Any]:
        return self._sessions.get(self._current_episode_id, {})

    @property
    def state(self) -> CloudState:
        s = self._session()
        return s.get("state", CloudState())

    # ── reset ─────────────────────────────────────────────
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
            message = (
                "EASY TASK: One server has 0% CPU and is wasting money. "
                "Terminate it to get under the $15.00/hr budget."
            )

        elif difficulty == "medium":
            servers = [
                {"server_id": "db-01",  "cpu": 10, "ram": "large",  "cost": 10.0},
                {"server_id": "web-01", "cpu": 85, "ram": "medium", "cost": 5.0},
            ]
            budget = 8.0
            message = (
                "MEDIUM TASK: The database is massively oversized for 10% CPU load. "
                "Resize db-01 to 'small' ($2.00/hr) to meet the $8.00/hr budget."
            )

        else:  # hard
            servers = [
                {"server_id": "web-01", "cpu": 90, "ram": "medium", "cost": 5.0},
                {"server_id": "web-02", "cpu": 5,  "ram": "large",  "cost": 10.0},
                {"server_id": "db-01",  "cpu": 0,  "ram": "small",  "cost": 2.0},
            ]
            budget = 10.0
            message = (
                "HARD TASK: Budget is $10.00/hr. "
                "Terminate the 0% CPU server, resize the 5% CPU server to 'small'. "
                "Do NOT touch web-01 (90% CPU) — the website will crash."
            )

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

    # ── step ──────────────────────────────────────────────
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
            obs = CloudObservation(
                done=True, reward=0.0,
                system_message="No active session. Call reset() first.",
                active_servers=[], current_hourly_cost=0.0,
                budget_limit=0.0, website_status="Offline"
            )
            return obs

        state: CloudState = sess["state"]
        servers = sess["servers"]
        sess["step_count"] += 1
        state.step_count += 1

        reward = 0.0
        message = f"Executed: {action.command}."

        # ── TERMINATE ────────────────────────────────────
        if action.command == "terminate" and action.server_id:
            server = next((s for s in servers if s["server_id"] == action.server_id), None)
            if server:
                if server["cpu"] > 50:
                    state.website_crashed = True
                    message = (
                        f"CRITICAL: Terminated {action.server_id} "
                        f"({server['cpu']}% CPU). Website is now OFFLINE."
                    )
                    reward = -0.5
                else:
                    servers.remove(server)
                    message = f"Terminated {action.server_id} ({server['cpu']}% CPU). Cost reduced."
                    reward = 0.2
            else:
                message = f"Error: server '{action.server_id}' not found."
                reward = -0.1

        # ── RESIZE ───────────────────────────────────────
        elif action.command == "resize" and action.server_id and action.new_size:
            server = next((s for s in servers if s["server_id"] == action.server_id), None)
            if server:
                old_cost = server["cost"]
                server["ram"] = action.new_size
                server["cost"] = {"small": 2.0, "medium": 5.0, "large": 10.0}.get(action.new_size, server["cost"])
                saved = old_cost - server["cost"]
                message = f"Resized {action.server_id} to {action.new_size}. Saved ${saved:.2f}/hr."
                reward = 0.2
            else:
                message = f"Error: server '{action.server_id}' not found."
                reward = -0.1

        # ── WAIT ─────────────────────────────────────────
        else:
            message = "Waited. No changes made."
            reward = 0.0

        # ── update cost ──────────────────────────────────
        sess["hourly_cost"] = sum(s["cost"] for s in servers)
        state.current_cost = sess["hourly_cost"]

        # ── episode end logic ────────────────────────────
        done = (
            sess["step_count"] >= sess["step_limit"]
            or state.website_crashed
        )

        if sess["hourly_cost"] <= sess["budget"] and not state.website_crashed:
            state.target_achieved = True
            done = True
            reward += 0.5  # completion bonus → total possible: 1.0
        
        # Episode Boundary Logic
        done = self._current_step >= self._step_limit or self._state.website_crashed
        if self._hourly_cost <= self._budget and not self._state.website_crashed:
            self._state.target_achieved = True
            done = True
            reward += 0.5 

        # <-- ADD THESE TWO LINES -->
        if done:
            GLOBAL_LAST_SCORE = 1.0 if self._state.target_achieved else 0.0
        obs = self._make_observation(self._current_episode_id, message)
        obs.done = done
        obs.reward = reward
        return obs

    # ── internal ─────────────────────────────────────────
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