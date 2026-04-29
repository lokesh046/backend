# chat_service/mcp_router.py

class MCPRouter:

    def route(self, state):

        steps = []

        # FIRE required?
        if state.fire_number is None:
            steps.append({"tool": "calculate_fire"})

        # Health score always after FIRE
        steps.append({"tool": "calculate_health_score"})

        # Loan optimizer if full loan info available
        if state.loan_amount and state.loan_interest_rate and state.loan_years:
            steps.append({"tool": "optimize_loan"})

        return {
            "goal": "financial_analysis",
            "steps": steps
        }