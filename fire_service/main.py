from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Union
import uuid

from .fire_engine import calculate_fire_plan
from shared.services.service_auth import get_current_user, CurrentUser

app = FastAPI(
    title="Fire Service",
    description="FIRE (Financial Independence, Retire Early) Calculation Service"
)


class FireInput(BaseModel):
    monthly_income: float
    living_expense: float
    current_savings: float
    return_rate: float
    inflation_rate: float
    has_loan: bool
    loan_emi: float = 0
    loan_years: int = 0


class FireResponse(BaseModel):
    fire_number: float
    fire_year: Union[int, str]  # Can be int or error message string
    final_wealth: float
    monthly_savings_needed: float
    savings_rate: float
    user_id: str
    status: str = "success"  # success or error


@app.post("/fire", response_model=FireResponse)
def calculate_fire(
    data: FireInput,
    user: CurrentUser = Depends(get_current_user)
):
    """
    Calculate FIRE (Financial Independence) numbers.
    Requires authentication.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    result = calculate_fire_plan(
        monthly_income=data.monthly_income,
        living_expense=data.living_expense,
        current_savings=data.current_savings,
        return_rate=data.return_rate,
        inflation_rate=data.inflation_rate,
        has_loan=data.has_loan,
        loan_emi=data.loan_emi,
        loan_years=data.loan_years
    )

    # Handle error cases (string responses)
    fire_year = result["fire_year"]
    if isinstance(fire_year, str):
        return FireResponse(
            fire_number=result["fire_number"],
            fire_year=fire_year,
            final_wealth=result["final_wealth"],
            monthly_savings_needed=result.get("monthly_savings_needed", 0),
            savings_rate=result.get("savings_rate", 0),
            user_id=user.id,
            status="error"
        )

    return FireResponse(
        fire_number=result["fire_number"],
        fire_year=fire_year,
        final_wealth=result["final_wealth"],
        monthly_savings_needed=result.get("monthly_savings_needed", 0),
        savings_rate=result.get("savings_rate", 0),
        user_id=user.id,
        status="success"
    )


@app.get("/health")
def health_check():
    """Public health check endpoint"""
    return {"status": "healthy", "service": "fire_service"}


@app.get("/protected")
def protected_endpoint(user: CurrentUser = Depends(get_current_user)):
    """Test endpoint to verify authentication"""
    return {
        "message": "You are authenticated!",
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    }
