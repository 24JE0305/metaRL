from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from models import CloudAction, CloudObservation, CloudState

class CloudOptimizerClient(EnvClient[CloudAction, CloudObservation, CloudState]):
    """Client for remote connection to the Cloud Optimizer Environment."""
    
    def _step_payload(self, action: CloudAction) -> dict:
        return action.model_dump()

    def _parse_result(self, payload: dict) -> StepResult:
        obs_data = payload.get("observation", {})
        return StepResult(
            observation=CloudObservation(**obs_data),
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> CloudState:
        return CloudState(**payload)