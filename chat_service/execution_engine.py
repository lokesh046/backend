# chat_service/execution_engine.py

from .tool_executor import execute_tool

class ExecutionEngine:

    async def execute_chain(self, tools, state, auth_token: str = None):

        results = {}

        for tool in tools:

            payload = {
                k: v for k, v in state.to_dict().items()
                if v is not None
            }

            result = await execute_tool(tool, payload, auth_token)

            # Use proper update method
            state.update_from_tool(tool, result)

            results[tool] = result

        return state, results