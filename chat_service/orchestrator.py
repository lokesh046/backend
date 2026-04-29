# chat_service/orchestrator.py

from .financial_state import FinancialState
from .financial_interpreter import FinancialInterpreter
from .financial_sanity import FinancialSanityEngine
from .guardrails import Guardrails
from .planner import Planner
from .execution_engine import ExecutionEngine
from .explanation_engine import ExplanationEngine


class FinancialOrchestrator:

    def __init__(self, llm_client):
        self.interpreter = FinancialInterpreter(llm_client)
        self.planner = Planner(llm_client)
        self.executor = ExecutionEngine()
        self.explainer = ExplanationEngine(llm_client)
        self.guardrails = Guardrails()
        self.sanity = FinancialSanityEngine()

    async def handle_request(self, message, auth_token: str = None, history: list = None, previous_state_dict: dict = None):
        
        # 0️⃣ Instantiate State and Merge Previous
        state = FinancialState()
        if previous_state_dict:
            # We filter out Nones so we don't accidentally overwrite existing valid data
            clean_prev = {k: v for k, v in previous_state_dict.items() if v is not None}
            state.__dict__.update(clean_prev)

        # 1️⃣ Extract new financial data
        extracted_data = await self.interpreter.extract(message, history=history)

        # 2️⃣ Merge Extraction into State
        # Only overwrite if the new extraction actually found something
        for k, v in extracted_data.items():
            if v is not None:
                setattr(state, k, v)
                
        # 🔥 Ensure default investment assumptions
        if state.return_rate is None:
            state.return_rate = 0.10

        if state.inflation_rate is None:
            state.inflation_rate = 0.06

        # 3️⃣ Hard validation
        self.guardrails.validate(state)

        # 4️⃣ Sanity validation & Missing Field Prompting
        # Instead of failing on 0 income, let's gracefully ask if missing
        missing_prompts = []
        if state.monthly_income is None:
            missing_prompts.append("What is your approximate monthly income?")
        elif state.living_expense is None:
            missing_prompts.append("Got it. And what are your average monthly living expenses?")
        elif state.current_savings is None:
            missing_prompts.append("Could you also tell me your total current savings or investments?")
        elif state.has_loan is None:
            missing_prompts.append("Do you currently have any active loans? If so, what is your monthly EMI?")
            
        if missing_prompts:
            # Return early with a conversational prompt
            return {
                "state": state.to_dict(),
                "tools_used": [],
                "tool_results": {},
                "advisor_explanation": missing_prompts[0],
                "flags": []
            }

        # Validate fully populated data
        valid, warnings = self.sanity.validate(state)

        if not valid:
            return {
                "error": "Invalid financial input",
                "details": warnings,
                "state": state.to_dict() # Pass state back so they don't lose it
            }

        # 5️⃣ Tool Planning
        tools_to_run = await self.planner.create_plan(state)

        tool_results = {}

        # 6️⃣ Execute Tools (with auth token)
        if tools_to_run:
            state, tool_results = await self.executor.execute_chain(
                tools_to_run,
                state,
                auth_token
            )

        # 7️⃣ Explanation
        explanation = await self.explainer.generate(state)

        return {
            "state": state.to_dict(),
            "tools_used": tools_to_run,
            "tool_results": tool_results,
            "advisor_explanation": explanation,
            "flags": state.flags
        }