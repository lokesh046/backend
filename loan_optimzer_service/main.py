from fastapi import FastAPI, HTTPException, Depends, status, Header
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from .loan_engine import (
    calculate_emi,
    generate_amortization_schedule,
    suggest_optimal_emi,
    normalize_interest_rate
)
from shared.services.service_auth import get_current_user, CurrentUser, decode_token

app = FastAPI(
    title="Loan Optimizer Service",
    description="Advanced Loan Analysis and Optimization Service",
    version="2.0"
)


class LoanInput(BaseModel):
    loan_amount: float = Field(..., gt=0)
    interest_rate_value: float = Field(..., gt=0)
    rate_type: str = Field(..., pattern="^(annual|monthly)$")
    tenure_years: int = Field(..., gt=0)


class EMIOption(BaseModel):
    emi: float
    months_to_payoff: int
    total_interest_paid: float


class OptimizationResult(BaseModel):
    emi_options: List[EMIOption]
    recommended_option: EMIOption


class LoanResponse(BaseModel):
    calculated_emi: float
    months_to_payoff: int
    total_interest_paid: float
    optimal_emi_suggestions: OptimizationResult
    user_id: str


def verify_internal_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Verify internal API key for service-to-service calls"""
    if x_api_key:
        return True
    return False


@app.post("/loan-analysis", response_model=LoanResponse)
async def analyze_loan(
    data: LoanInput,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    """
    Analyze loan and provide optimization suggestions.
    Requires authentication via JWT Bearer token or X-API-Key.
    """
    user: Optional[CurrentUser] = None
    
    if authorization:
        try:
            token = authorization.replace("Bearer ", "")
            user = await get_current_user_from_token(token)
        except Exception:
            pass
    elif x_api_key:
        user = CurrentUser(id="service", email="service@internal", role="service")
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        annual_rate = normalize_interest_rate(
            data.interest_rate_value,
            data.rate_type
        )

        emi = calculate_emi(
            data.loan_amount,
            annual_rate,
            data.tenure_years
        )

        amortization = generate_amortization_schedule(
            data.loan_amount,
            annual_rate,
            emi
        )

        optimization = suggest_optimal_emi(
            data.loan_amount,
            annual_rate,
            data.tenure_years
        )

        emi_options = [
            EMIOption(**option)
            for option in optimization["emi_options"]
        ]

        recommended = EMIOption(**optimization["recommended_option"])

        return LoanResponse(
            calculated_emi=emi,
            months_to_payoff=amortization["months_to_payoff"],
            total_interest_paid=amortization["total_interest_paid"],
            optimal_emi_suggestions=OptimizationResult(
                emi_options=emi_options,
                recommended_option=recommended
            ),
            user_id=user.id if user else "anonymous"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def get_current_user_from_token(token: str) -> CurrentUser:
    """Helper to get user from token"""
    from jose import jwt, JWTError
    
    SECRET_KEY = "your_super_secret_key_change_this"
    ALGORITHM = "HS256"
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email", "")
        role = payload.get("role", "user")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return CurrentUser(
            id=user_id,
            email=email,
            role=role
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@app.get("/health")
def health_check():
    """Public health check endpoint"""
    return {"status": "healthy", "service": "loan_optimizer_service"}


@app.get("/protected")
async def protected_endpoint(
    authorization: Optional[str] = Header(None)
):
    """Test endpoint to verify authentication"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    user = await get_current_user_from_token(authorization.replace("Bearer ", ""))
    
    return {
        "message": "You are authenticated!",
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    }
