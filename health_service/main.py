from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel

from .financial_health_score import calculate_financial_health_score
from shared.services.service_auth import get_current_user, CurrentUser

app = FastAPI(
    title="Health Score Service",
    description="Financial Health Scoring Service"
)


class HealthInput(BaseModel):
    monthly_income: float
    living_expense: float
    loan_emi: float
    current_savings: float
    fire_number: float
    has_insurance: str


class HealthResponse(BaseModel):
    financial_health_score: float
    user_id: str
    grade: str
    breakdown: dict


@app.post("/health-score", response_model=HealthResponse)
def calculate_health(
    data: HealthInput,
    user: CurrentUser = Depends(get_current_user)
):
    """
    Calculate financial health score.
    Requires authentication.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    score = calculate_financial_health_score(
        monthly_income=data.monthly_income,
        living_expense=data.living_expense,
        loan_emi=data.loan_emi,
        current_savings=data.current_savings,
        fire_number=data.fire_number,
        has_insurance=data.has_insurance
    )

    grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"

    return HealthResponse(
        financial_health_score=score,
        user_id=user.id,
        grade=grade,
        breakdown={
            "savings_ratio": (data.current_savings / data.monthly_income) if data.monthly_income > 0 else 0,
            "debt_ratio": (data.loan_emi / data.monthly_income) if data.monthly_income > 0 else 0
        }
    )


@app.get("/health")
def health_check():
    """Public health check endpoint"""
    return {"status": "healthy", "service": "health_service"}


@app.get("/protected")
def protected_endpoint(user: CurrentUser = Depends(get_current_user)):
    """Test endpoint to verify authentication"""
    return {
        "message": "You are authenticated!",
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    }
