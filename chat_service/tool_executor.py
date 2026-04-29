# chat_service/tool_executor.py

import logging
from fire_service.fire_engine import calculate_fire_plan
from health_service.financial_health_score import calculate_financial_health_score
from loan_optimzer_service.loan_engine import (
    calculate_emi, 
    generate_amortization_schedule, 
    suggest_optimal_emi, 
    normalize_interest_rate
)

async def execute_tool(tool_name, payload, auth_token: str = None):
    """
    Execute tool by directly calling internal logic functions (monolithic architecture).
    """
    
    try:
        if tool_name == "calculate_fire":
            has_loan = False
            if "has_loan" in payload:
                val = payload["has_loan"]
                has_loan = (str(val).lower() == "yes") if isinstance(val, str) else bool(val)
                
            return calculate_fire_plan(
                monthly_income=payload.get("monthly_income", 0),
                living_expense=payload.get("living_expense", 0),
                current_savings=payload.get("current_savings", 0),
                return_rate=payload.get("return_rate", 0.1),
                inflation_rate=payload.get("inflation_rate", 0.06),
                has_loan=has_loan,
                loan_emi=payload.get("loan_emi", 0),
                loan_years=payload.get("loan_years", 0)
            )
            
        elif tool_name == "calculate_health_score":
            has_insurance = "no"
            if "has_insurance" in payload:
                val = payload["has_insurance"]
                has_insurance = "yes" if val and str(val).lower() != "no" else "no"

            score = calculate_financial_health_score(
                monthly_income=payload.get("monthly_income", 0),
                living_expense=payload.get("living_expense", 0),
                loan_emi=payload.get("loan_emi", 0),
                current_savings=payload.get("current_savings", 0),
                fire_number=payload.get("fire_number", 0),
                has_insurance=has_insurance
            )
            grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
            return {"financial_health_score": score, "grade": grade}

        elif tool_name == "optimize_loan":
            loan_amount = payload.get("loan_amount", 0)
            interest_rate = payload.get("interest_rate_value", 0)
            tenure_years = payload.get("tenure_years", 1)
            rate_type = payload.get("rate_type", "annual")
            
            annual_rate = normalize_interest_rate(interest_rate, rate_type)
            emi = calculate_emi(loan_amount, annual_rate, tenure_years)
            amortization = generate_amortization_schedule(loan_amount, annual_rate, emi)
            optimization = suggest_optimal_emi(loan_amount, annual_rate, tenure_years)
            
            return {
                "calculated_emi": emi,
                "months_to_payoff": amortization["months_to_payoff"],
                "total_interest_paid": amortization["total_interest_paid"],
                "optimal_emi_suggestions": optimization
            }
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logging.error(f"Error executing tool {tool_name}: {e}")
        return {"error": str(e)}