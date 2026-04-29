import copy
from .execution_engine import ExecutionEngine


class ScenarioEngine:

    def __init__(self):
        self.executor = ExecutionEngine()

    async def simulate(self, base_state, modifications: dict):

        scenario_state = copy.deepcopy(base_state)

        # Apply modifications
        for key, value in modifications.items():
            if value is not None:
                setattr(scenario_state, key, value)

        scenario_state.invalidate_fire()

        plan = {
            "goal": "scenario_simulation",
            "steps": [
                {"tool": "calculate_fire"},
                {"tool": "calculate_health_score"}
            ]
        }

        scenario_state, tool_used, tool_result = \
            await self.executor.execute_plan(plan, scenario_state)

        return scenario_state