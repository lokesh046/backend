TOOLS = [
    {
        "name": "calculate_fire",
        "description": "Calculate FIRE number and years to financial independence",
        "parameters": {
            "type": "object",
            "properties": {
                "monthly_income": {"type": "number"},
                "living_expense": {"type": "number"},
                "current_savings": {"type": "number"},
                "return_rate": {"type": "number"},
                "inflation_rate": {"type": "number"},
                "loan_emi": {"type": "number"},
                "loan_years": {"type": "integer"}
            },
            "required": ["monthly_income", "living_expense", "current_savings"]
        }
    },
    {
        "name": "optimize_loan",
        "description": "Optimize loan EMI and generate payoff strategy",
        "parameters": {
            "type": "object",
            "properties": {
                "loan_amount": {"type": "number"},
                "interest_rate_value": {"type": "number"},
                "rate_type": {"type": "string"},
                "tenure_years": {"type": "integer"}
            },
            "required": ["loan_amount", "interest_rate_value", "tenure_years"]
        }
    }
]
