# chat_service/guardrails.py

class Guardrails:

    def validate(self, state):

        if state.monthly_income is not None and state.monthly_income <= 0:
            raise ValueError("Monthly income must be greater than zero.")

        if state.living_expense is not None and state.living_expense < 0:
            raise ValueError("Living expense cannot be negative.")

        if state.loan_emi is not None and state.loan_emi < 0:
            raise ValueError("Loan EMI cannot be negative.")

        # Safe access example
        if getattr(state, "has_insurance", None) is None:
            # Health service expects a string ("yes"/"no")
            state.has_insurance = "no"