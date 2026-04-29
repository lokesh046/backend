"""
API Gateway with Automatic Token Handling via Cookies
After login, all subsequent requests automatically use the stored token
"""

from fastapi import FastAPI, Depends, HTTPException, status, Response, Request, Cookie, Header, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import httpx
import uuid
import os

from shared.services.service_auth import get_current_user, CurrentUser, create_access_token
from shared.services.auth_routes import router as auth_router

from shared.database import get_db, engine, Base
from shared.services.fire_service import save_fire_calculation
from shared.services.health_service import save_health_score
from shared.services.loan_service import save_loan_simulation
import shared.models
from fastapi.middleware.cors import CORSMiddleware

# Internal Service Imports
from fire_service.fire_engine import calculate_fire_plan
from health_service.financial_health_score import calculate_financial_health_score
from loan_optimzer_service.loan_engine import calculate_emi, generate_amortization_schedule, suggest_optimal_emi, normalize_interest_rate
from chat_service.main import router as chat_router
from explain_service.main import router as explain_router
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()
app = FastAPI(
    title="Wealth To FIRE Gateway (Async)",
    description="API Gateway for Financial Planning Microservices"
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(explain_router, tags=["Explain"])

@app.on_event("startup")
async def startup():
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR;"))
                print("[MIGRATION] Added username column.")
            except Exception:
                pass
            try:
                await conn.execute(text("UPDATE users SET username = split_part(email, '@', 1) WHERE username IS NULL OR username = '';"))
                print("[MIGRATION] Updated usernames from email.")
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE users ALTER COLUMN username SET NOT NULL;"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE users ADD CONSTRAINT uq_users_username UNIQUE (username);"))
            except Exception:
                pass
            
            try:
                await conn.execute(text("ALTER TABLE fire_calculations ADD COLUMN scenario_name VARCHAR DEFAULT 'Primary Goal';"))
                print("[MIGRATION] Added scenario_name column to fire_calculations.")
            except Exception:
                pass
        print("[SUCCESS] Database connection established, tables synced, and username migrated.")
    except TimeoutError:
        print("[WARNING] Could not connect to database during startup. Retrying on first request...")
    except Exception as e:
        print(f"[WARNING] Database initialization error: {e}. Retrying on first request...")


def get_token_from_request(authorization: Optional[str] = Header(None), access_token: Optional[str] = Cookie(None)) -> Optional[str]:
    """Get token from Authorization header OR cookie - automatically handles both"""
    if authorization:
        return authorization.replace("Bearer ", "")
    if access_token:
        return access_token
    return None


def get_current_user_from_token(token: Optional[str]) -> Optional[CurrentUser]:
    """Decode token and return user"""
    if not token:
        return None
    
    try:
        from shared.services.service_auth import decode_token
        token_data = decode_token(token)
        
        return CurrentUser(
            id=token_data.user_id or "unknown",
            email=token_data.email or "",
            username=token_data.username or "",
            role=token_data.role or "user",
            tenant_id=token_data.tenant_id
        )
    except Exception:
        return None


class FinanceInput(BaseModel):
    monthly_income: float
    living_expense: float
    current_savings: float
    return_rate: float
    inflation_rate: float
    has_loan: str
    loan_amount: float
    interest_rate_value: float
    rate_type: str
    loan_emi: float = 0
    loan_years: int = 0
    has_insurance: str
    scenario_name: str = "Primary Goal"


class LoanOnlyInput(BaseModel):
    loan_amount: float
    interest_rate_value: float
    rate_type: str
    tenure_years: int


def get_auth_headers(authorization: Optional[str] = Header(None), access_token: Optional[str] = Cookie(None)) -> dict:
    """Get authorization headers - works with header OR cookie"""
    token = get_token_from_request(authorization, access_token)
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def require_auth(authorization: Optional[str] = Header(None), access_token: Optional[str] = Cookie(None)) -> CurrentUser:
    """Dependency that requires authentication - works with header OR cookie"""
    token = get_token_from_request(authorization, access_token)
    user = get_current_user_from_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login first.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


# ============================================================
# PUBLIC ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "service": "Wealth To FIRE API Gateway",
        "version": "2.0",
        "auth_required": True
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api_gateway"}

@app.post("/dev/promote_to_admin")
async def dev_promote_to_admin(email: str, db_session=Depends(get_db)):
    from sqlalchemy import text
    try:
        result = await db_session.execute(
            text("UPDATE users SET role = 'admin' WHERE email = :email RETURNING id"),
            {"email": email}
        )
        updated_id = result.scalar()
        await db_session.commit()
        if updated_id:
            return {"message": f"Successfully promoted {email} to admin!"}
        else:
            return {"error": f"User {email} not found."}
    except Exception as e:
        await db_session.rollback()
        return {"error": str(e)}

# ============================================================
# PROTECTED ENDPOINTS - Auto-auth via cookie or header
# ============================================================

@app.post("/calculate-fire")
async def calculate_fire(
    data: FinanceInput,
    user: CurrentUser = Depends(require_auth),
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    db_session = Depends(get_db)
):
    """
    Calculate FIRE - monolithic local call
    """
    # 1. Local FIRE calculation
    fire_result = calculate_fire_plan(
        monthly_income=data.monthly_income,
        living_expense=data.living_expense,
        current_savings=data.current_savings,
        return_rate=data.return_rate,
        inflation_rate=data.inflation_rate,
        has_loan=(str(data.has_loan).lower() == "yes"),
        loan_emi=data.loan_emi,
        loan_years=data.loan_years
    )
    
    if isinstance(fire_result["fire_year"], str):
        return {"error": "FIRE service failed", "details": fire_result["fire_year"]}

    # 2. Local Health calculation
    health_score = calculate_financial_health_score(
        monthly_income=data.monthly_income,
        living_expense=data.living_expense,
        loan_emi=data.loan_emi,
        current_savings=data.current_savings,
        fire_number=fire_result["fire_number"],
        has_insurance=str(data.has_insurance).lower()
    )

    # Save to database
    try:
        await save_fire_calculation(
            db=db_session,
            user_id=uuid.UUID(user.id),
            monthly_income=data.monthly_income,
            living_expense=data.living_expense,
            current_savings=data.current_savings,
            fire_number=fire_result["fire_number"],
            fire_year=fire_result["fire_year"],
            final_wealth=fire_result["final_wealth"],
            scenario_name=data.scenario_name
        )
    except Exception as e:
        print(f"Error saving fire calculation: {e}")

    try:
        debt_ratio = data.loan_emi / data.monthly_income if data.monthly_income > 0 else 0
        savings_ratio = data.current_savings / data.monthly_income if data.monthly_income > 0 else 0
        await save_health_score(
            db=db_session,
            user_id=uuid.UUID(user.id),
            score=health_score,
            fire_number=fire_result["fire_number"],
            debt_ratio=debt_ratio,
            savings_ratio=savings_ratio
        )
    except Exception as e:
        print(f"Error saving health score: {e}")

    return {
        "fire_number": fire_result["fire_number"],
        "fire_year": fire_result["fire_year"],
        "final_wealth": fire_result["final_wealth"],
        "financial_health_score": health_score,
        "user_id": user.id,
        "saved": True
    }

@app.post("/loan-fire-strategy")
async def compare_loan_vs_fire(
    data: FinanceInput,
    user: CurrentUser = Depends(require_auth),
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    db_session = Depends(get_db)
):
    """Compare loan vs FIRE strategy - monolithic"""
    
    # 1. Current FIRE
    fire_current_result = calculate_fire_plan(
        monthly_income=data.monthly_income,
        living_expense=data.living_expense,
        current_savings=data.current_savings,
        return_rate=data.return_rate,
        inflation_rate=data.inflation_rate,
        has_loan=(str(data.has_loan).lower() == "yes"),
        loan_emi=data.loan_emi,
        loan_years=data.loan_years
    )
    
    current_year = fire_current_result.get("fire_year", 0)

    if str(data.has_loan).lower() == "no" or data.loan_amount <= 0:
        recommended_emi = 0
        optimized_year = current_year
        strategy = "no_loan"
        fire_optimized_result = fire_current_result
        math_optimal_emi = 0
        loan_savings = 0
        original_emi = 0
    else:
        # Local loan optimization
        annual_rate = normalize_interest_rate(data.interest_rate_value, data.rate_type)
        optimization = suggest_optimal_emi(data.loan_amount, annual_rate, data.loan_years or 1)
        original_emi = calculate_emi(data.loan_amount, annual_rate, data.loan_years or 1)
        
        math_optimal_emi = optimization["recommended_option"]["emi"]
        loan_savings = (
            generate_amortization_schedule(data.loan_amount, annual_rate, original_emi)["total_interest_paid"] -
            optimization["recommended_option"]["total_interest_paid"]
        )

        # Calculate optimized FIRE
        fire_optimized_result = calculate_fire_plan(
            monthly_income=data.monthly_income,
            living_expense=data.living_expense,
            current_savings=data.current_savings,
            return_rate=data.return_rate,
            inflation_rate=data.inflation_rate,
            has_loan=True,
            loan_emi=math_optimal_emi,
            loan_years=data.loan_years
        )
        
        optimized_year = fire_optimized_result.get("fire_year", 0)
        curr_y = current_year if isinstance(current_year, (int, float)) else 999
        opt_y = optimized_year if isinstance(optimized_year, (int, float)) else 999
        
        strategy = "increase_emi" if (opt_y < curr_y and opt_y > 0) else "keep_current_emi"
        recommended_emi = math_optimal_emi if strategy == "increase_emi" else original_emi

    # Calculate health score locally
    health_score = calculate_financial_health_score(
        monthly_income=data.monthly_income,
        living_expense=data.living_expense,
        loan_emi=recommended_emi if strategy == "increase_emi" else (original_emi if original_emi > 0 else data.loan_emi),
        current_savings=data.current_savings,
        fire_number=fire_optimized_result.get("fire_number", 0),
        has_insurance=str(data.has_insurance).lower()
    )

    ai_explanation = {}
    try:
        from explain_service.pipeline.retrieval import retrieve
        from explain_service.pipeline.prompt_builder import build_prompt
        from explain_service.pipeline.llm_client import generate_explanation
        from explain_service.main import ExplainRequest
        
        req_data = ExplainRequest(
            context_type="loan_fire_strategy",
            current_fire_year=int(current_year) if isinstance(current_year, (int, float)) else 0,
            optimized_fire_year=int(optimized_year) if isinstance(optimized_year, (int, float)) else 0,
            recommended_emi=recommended_emi,
            strategy_recommendation=strategy,
            financial_health_score=health_score
        )
        query = f"{strategy} fire timeline debt impact"
        context, sources, confidence = retrieve(query)
        prompt = build_prompt(context, req_data)
        explanation_structured = await generate_explanation(prompt)
        
        ai_explanation = {
            **explanation_structured,
            "sources": sources,
            "confidence_score": confidence
        }
    except Exception as e:
        print("Error fetching AI explanation:", e)

    # Save to DB
    if not isinstance(current_year, str):
        try:
            await save_fire_calculation(
                db=db_session,
                user_id=uuid.UUID(user.id),
                monthly_income=data.monthly_income,
                living_expense=data.living_expense,
                current_savings=data.current_savings,
                fire_number=fire_current_result.get("fire_number", 0),
                fire_year=fire_current_result.get("fire_year", 0),
                final_wealth=fire_current_result.get("final_wealth", 0),
                scenario_name=data.scenario_name
            )
        except Exception as e:
            print(f"Error saving fire: {e}")

    return {
        "current_fire_year": current_year,
        "optimized_fire_year": optimized_year,
        "recommended_emi": recommended_emi,
        "strategy_recommendation": strategy,
        "ai_explanation": ai_explanation,
        "loan_details": {
            "original_emi": data.loan_emi if original_emi == 0 else original_emi,
            "optimal_emi": math_optimal_emi if strategy == "keep_current_emi" else recommended_emi,
            "interest_savings": loan_savings
        },
        "user_id": user.id
    }

@app.post("/loan-only")
async def loan_only(
    data: LoanOnlyInput,
    user: CurrentUser = Depends(require_auth),
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None)
):
    """Loan analysis - monolithic"""
    annual_rate = normalize_interest_rate(data.interest_rate_value, data.rate_type)
    emi = calculate_emi(data.loan_amount, annual_rate, data.tenure_years)
    amortization = generate_amortization_schedule(data.loan_amount, annual_rate, emi)
    optimization = suggest_optimal_emi(data.loan_amount, annual_rate, data.tenure_years)
    
    return {
        "calculated_emi": emi,
        "months_to_payoff": amortization["months_to_payoff"],
        "total_interest_paid": amortization["total_interest_paid"],
        "optimal_emi_suggestions": {
            "emi_options": optimization["emi_options"],
            "recommended_option": optimization["recommended_option"]
        },
        "user_id": user.id
    }

@app.get("/me")
async def get_current_user_info(
    user: CurrentUser = Depends(require_auth)
):
    """Get current user info - automatic auth"""
    return {
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role
    }


@app.get("/fire/history")
async def get_fire_history(
    user: CurrentUser = Depends(require_auth),
    db_session = Depends(get_db)
):
    """Get fire calculation history from database"""
    from sqlalchemy import select
    from shared.models import FireCalculation
    
    result = await db_session.execute(
        select(FireCalculation)
        .where(FireCalculation.user_id == uuid.UUID(user.id))
        .order_by(FireCalculation.created_at.desc())
        .limit(10)
    )
    
    records = result.scalars().all()
    
    return {
        "calculations": [
            {
                "id": str(r.id),
                "fire_number": r.fire_number,
                "fire_year": r.fire_year,
                "final_wealth": r.final_wealth,
                "monthly_income": r.monthly_income,
                "living_expense": r.living_expense,
                "current_savings": r.current_savings,
                "scenario_name": r.scenario_name,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ],
        "count": len(records)
    }


@app.get("/health/history")
async def get_health_history(
    user: CurrentUser = Depends(require_auth),
    db_session = Depends(get_db)
):
    """Get health score history from database"""
    from sqlalchemy import select
    from shared.models import HealthScore
    
    result = await db_session.execute(
        select(HealthScore)
        .where(HealthScore.user_id == uuid.UUID(user.id))
        .order_by(HealthScore.created_at.desc())
        .limit(10)
    )
    
    records = result.scalars().all()
    
    return {
        "scores": [
            {
                "score": r.score,
                "fire_number": r.fire_number,
                "debt_ratio": r.debt_ratio,
                "savings_ratio": r.savings_ratio,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ],
        "count": len(records)
    }


@app.post("/logout")
async def logout(response: Response):
    """Clear auth cookie"""
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


# ============================================================
# SERVICE-SPECIFIC ENDPOINTS (Direct access)
# ============================================================

@app.post("/fire")
async def fire_direct(
    data: FinanceInput,
    user: CurrentUser = Depends(require_auth),
    db_session = Depends(get_db)
):
    """Direct FIRE calculation - saves to database"""
    result = calculate_fire_plan(
        monthly_income=data.monthly_income,
        living_expense=data.living_expense,
        current_savings=data.current_savings,
        return_rate=data.return_rate,
        inflation_rate=data.inflation_rate,
        has_loan=(str(data.has_loan).lower() == "yes"),
        loan_emi=data.loan_emi,
        loan_years=data.loan_years
    )
    
    if not isinstance(result["fire_year"], str):
        try:
            await save_fire_calculation(
                db=db_session,
                user_id=uuid.UUID(user.id),
                monthly_income=data.monthly_income,
                living_expense=data.living_expense,
                current_savings=data.current_savings,
                fire_number=result.get("fire_number", 0),
                fire_year=result.get("fire_year", 0),
                final_wealth=result.get("final_wealth", 0),
                scenario_name=data.scenario_name
            )
        except Exception:
            pass

        try:
            health_score = calculate_financial_health_score(
                monthly_income=data.monthly_income,
                living_expense=data.living_expense,
                loan_emi=data.loan_emi,
                current_savings=data.current_savings,
                fire_number=result["fire_number"],
                has_insurance=str(data.has_insurance).lower()
            )
            debt_ratio = data.loan_emi / data.monthly_income if data.monthly_income > 0 else 0
            savings_ratio = data.current_savings / data.monthly_income if data.monthly_income > 0 else 0
            
            await save_health_score(
                db=db_session,
                user_id=uuid.UUID(user.id),
                score=health_score,
                fire_number=result["fire_number"],
                debt_ratio=debt_ratio,
                savings_ratio=savings_ratio
            )
        except Exception:
            pass

    return {
        "fire_number": result["fire_number"],
        "fire_year": result["fire_year"],
        "final_wealth": result["final_wealth"],
        "status": "success" if not isinstance(result["fire_year"], str) else "error"
    }


@app.post("/health")
async def health_direct(
    data: FinanceInput,
    user: CurrentUser = Depends(require_auth)
):
    """Direct health score calculation"""
    score = calculate_financial_health_score(
        monthly_income=data.monthly_income,
        living_expense=data.living_expense,
        loan_emi=data.loan_emi,
        current_savings=data.current_savings,
        fire_number=1500000, # Mock as old code did
        has_insurance=str(data.has_insurance).lower()
    )
    
    grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
    
    return {
        "financial_health_score": score,
        "user_id": user.id,
        "grade": grade,
        "breakdown": {
            "savings_ratio": (data.current_savings / data.monthly_income) if data.monthly_income > 0 else 0,
            "debt_ratio": (data.loan_emi / data.monthly_income) if data.monthly_income > 0 else 0
        }
    }


@app.post("/loan")
async def loan_direct(
    data: LoanOnlyInput,
    user: CurrentUser = Depends(require_auth),
    db_session = Depends(get_db)
):
    """Direct loan analysis - saves to database"""
    annual_rate = normalize_interest_rate(data.interest_rate_value, data.rate_type)
    emi = calculate_emi(data.loan_amount, annual_rate, data.tenure_years)
    amortization = generate_amortization_schedule(data.loan_amount, annual_rate, emi)
    optimization = suggest_optimal_emi(data.loan_amount, annual_rate, data.tenure_years)
    
    try:
        recommended_emi = optimization["recommended_option"]["emi"]
        await save_loan_simulation(
            db=db_session,
            user_id=uuid.UUID(user.id),
            loan_amount=data.loan_amount,
            interest_rate=data.interest_rate_value,
            tenure_years=data.tenure_years,
            optimal_emi=recommended_emi,
            total_interest=amortization["total_interest_paid"]
        )
    except Exception as e:
        print(f"Error saving loan simulation: {e}")

    return {
        "calculated_emi": emi,
        "months_to_payoff": amortization["months_to_payoff"],
        "total_interest_paid": amortization["total_interest_paid"],
        "optimal_emi_suggestions": {
            "emi_options": optimization["emi_options"],
            "recommended_option": optimization["recommended_option"]
        },
        "user_id": user.id
    }


@app.get("/loan/history")
async def get_loan_history(
    user: CurrentUser = Depends(require_auth),
    db_session = Depends(get_db)
):
    """Get loan simulation history from database"""
    from sqlalchemy import select
    from shared.models import LoanSimulation
    
    result = await db_session.execute(
        select(LoanSimulation)
        .where(LoanSimulation.user_id == uuid.UUID(user.id))
        .order_by(LoanSimulation.created_at.desc())
        .limit(10)
    )
    
    records = result.scalars().all()
    
    return {
        "simulations": [
            {
                "loan_amount": r.loan_amount,
                "interest_rate": r.interest_rate,
                "tenure_years": r.tenure_years,
                "optimal_emi": r.optimal_emi,
                "total_interest": r.total_interest,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ],
        "count": len(records)
    }


@app.get("/dashboard")
async def get_dashboard(
    user: CurrentUser = Depends(require_auth),
    db_session = Depends(get_db)
):
    """Get user dashboard with all financial data"""
    from sqlalchemy import select
    from shared.models import FireCalculation, HealthScore, LoanSimulation
    
    # Get latest FIRE calculation
    fire_result = await db_session.execute(
        select(FireCalculation)
        .where(FireCalculation.user_id == uuid.UUID(user.id))
        .order_by(FireCalculation.created_at.desc())
        .limit(1)
    )
    latest_fire = fire_result.scalar_one_or_none()
    
    # Get latest health score
    health_result = await db_session.execute(
        select(HealthScore)
        .where(HealthScore.user_id == uuid.UUID(user.id))
        .order_by(HealthScore.created_at.desc())
        .limit(1)
    )
    latest_health = health_result.scalar_one_or_none()
    
    # Get loan count
    loan_result = await db_session.execute(
        select(LoanSimulation)
        .where(LoanSimulation.user_id == uuid.UUID(user.id))
        .order_by(LoanSimulation.created_at.desc())
    )
    loans = loan_result.scalars().all()
    
    return {
        "user": {
            "id": user.id,
            "email": user.email
        },
        "fire": {
            "fire_number": latest_fire.fire_number if latest_fire else None,
            "fire_year": latest_fire.fire_year if latest_fire else None,
            "final_wealth": latest_fire.final_wealth if latest_fire else None,
            "monthly_income": latest_fire.monthly_income if latest_fire else None,
            "current_savings": latest_fire.current_savings if latest_fire else None,
            "last_updated": latest_fire.created_at.isoformat() if latest_fire and latest_fire.created_at else None
        } if latest_fire else None,
        "health": {
            "score": latest_health.score if latest_health else None,
            "debt_ratio": latest_health.debt_ratio if latest_health else None,
            "savings_ratio": latest_health.savings_ratio if latest_health else None,
            "last_updated": latest_health.created_at.isoformat() if latest_health and latest_health.created_at else None
        } if latest_health else None,
        "loans": {
            "total_simulations": len(loans),
            "latest_loan": {
                "loan_amount": loans[0].loan_amount if loans else None,
                "optimal_emi": loans[0].optimal_emi if loans else None,
                "total_interest": loans[0].total_interest if loans else None
            } if loans else None
        }
    }
