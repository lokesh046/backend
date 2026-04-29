# chat_service/financial_sanity.py

class FinancialSanityEngine:

    def validate(self, state):

        errors = []
        warnings = []

        income = state.monthly_income if state.monthly_income is not None else 0
        expense = state.living_expense if state.living_expense is not None else 0
        savings = state.current_savings if state.current_savings is not None else 0
        emi = state.loan_emi if state.loan_emi is not None else 0

        # ===============================
        # 🔴 HARD BLOCK CONDITIONS
        # ===============================

        # Only error on income if it was actually provided as <= 0.
        # If it's None, the Orchestrator will ask for it.
        if state.monthly_income is not None and income <= 0:
            errors.append("Monthly income must be greater than zero.")

        if expense < 0:
            errors.append("Living expense cannot be negative.")

        if savings < 0:
            errors.append("Savings cannot be negative.")

        if emi > income:
            errors.append("EMI cannot exceed total monthly income.")

        if expense > income:
            warnings.append("Living expense exceeds income. Savings rate negative.")

        # ===============================
        # 🟡 RISK DETECTION CONDITIONS
        # ===============================

        if income > 0:
            savings_ratio = (income - expense - emi) / income

            if savings_ratio < 0:
                warnings.append("You are spending more than you earn.")

            if savings_ratio > 0.8:
                warnings.append("Savings rate unusually high. Verify inputs.")

        if income > 0 and emi > 0:
            emi_ratio = emi / income

            if emi_ratio > 0.7:
                warnings.append("EMI burden exceeds 70% of income. High risk.")

        if state.fire_year is not None:
            try:
                fire_year_val = float(state.fire_year)
                if fire_year_val < 3:
                    warnings.append("FIRE projected under 3 years. Verify realism.")
            except (ValueError, TypeError):
                # If it's a string like "Never" or "N/A", we ignore the check
                pass

        if state.return_rate and state.return_rate > 0.25:
            warnings.append("Return rate above 25% annually is highly optimistic.")

        # ===============================
        # 🚨 FRAUD / ANOMALY DETECTION
        # ===============================

        if income > 1_000_000:
            warnings.append("Unusually high monthly income detected.")

        if savings > income * 100:
            warnings.append("Savings far exceeds income. Verify data.")

        # Attach warnings to state
        for w in warnings:
            state.add_flag(w)

        if errors:
            return False, errors

        return True, warnings