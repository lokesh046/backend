# chat_service/explanation_engine.py

class ExplanationEngine:

    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate(self, state):

        prompt = f"""
        You are a concise financial advisor.

        Provide a very brief, direct explanation of the financial situation using the computed values below.

        IMPORTANT RULES:
        - Do NOT write long paragraphs. Keep it extremely short and concise (max 3-4 bullet points of actionable advice).
        - Focus ONLY on the most useful and practical insights.
        - Format ALL currency amounts with the Indian Rupee symbol (₹) strictly. Do NOT use USD ($).
        - Do NOT recalculate anything. Only use the numbers provided.

        Financial Data:
        Monthly Income: {state.monthly_income}
        Monthly Expense: {state.living_expense}
        Current Savings: {state.current_savings}
        Loan EMI: {state.loan_emi}
        FIRE Number: {state.fire_number}
        Years to FIRE: {state.fire_year}
        Final Wealth Projection: {state.final_wealth}
        Financial Health Score: {state.financial_health_score}
        """

        explanation = await self.llm.generate_text(prompt)

        return explanation