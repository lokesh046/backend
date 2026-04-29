from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from shared.database import get_db
from shared.services.auth import get_current_user
from shared.models.user import User
from shared.models.fire import FireCalculation
from shared.models.health import HealthScore
from shared.models.loan import LoanSimulation


router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1️⃣ Get Latest FIRE Calculation
    fire_query = await db.execute(
        select(FireCalculation)
        .where(FireCalculation.user_id == current_user.id)
        .order_by(desc(FireCalculation.created_at))
        .limit(1)
    )
    latest_fire = fire_query.scalar_one_or_none()

    # 2️⃣ Get Latest Health Score
    health_query = await db.execute(
        select(HealthScore)
        .where(HealthScore.user_id == current_user.id)
        .order_by(desc(HealthScore.created_at))
        .limit(1)
    )
    latest_health = health_query.scalar_one_or_none()

    # 3️⃣ Get Loan Simulations
    loan_query = await db.execute(
        select(LoanSimulation)
        .where(LoanSimulation.user_id == current_user.id)
        .order_by(desc(LoanSimulation.created_at))
    )
    loans = loan_query.scalars().all()

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "role": current_user.role
        },
        "latest_fire": latest_fire,
        "latest_health_score": latest_health,
        "loan_simulations": loans
    }