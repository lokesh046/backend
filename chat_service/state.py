# chat_service/state.py

from pydantic import BaseModel
from typing import Optional

class FinancialState(BaseModel):

    monthly_income: Optional[float] = None
    living_expense: Optional[float] = None
    current_savings: Optional[float] = None

    loan_amount: Optional[float] = None
    loan_emi: Optional[float] = None
    loan_years: Optional[int] = None
    loan_interest_rate: Optional[float] = None
    has_loan: Optional[bool] = None

    # 🔥 ADD THESE DEFAULTS
    return_rate: float = 0.10
    inflation_rate: float = 0.06

    has_insurance: Optional[str] = "no"

    fire_number: Optional[float] = None
    fire_year: Optional[int] = None
    final_wealth: Optional[float] = None
    financial_health_score: Optional[float] = None