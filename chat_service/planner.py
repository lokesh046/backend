class Planner:

    def __init__(self, llm_client=None):
        self.llm = llm_client

    async def create_plan(self, state):

        tools = []

        # Step 1️⃣ FIRE calculation
        if (
            state.monthly_income is not None and
            state.living_expense is not None and
            state.current_savings is not None
        ):
            tools.append("calculate_fire")

            # Step 2️⃣ Health score should run AFTER fire
            tools.append("calculate_health_score")

        return tools