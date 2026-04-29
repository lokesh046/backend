import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import LoanSimulation


async def save_loan_simulation(
    db: AsyncSession,
    user_id: uuid.UUID,
    loan_amount: float,
    interest_rate: float,
    tenure_years: int,
    optimal_emi: float,
    total_interest: float
):
    loan_record = LoanSimulation(
        id=uuid.uuid4(),
        user_id=user_id,
        loan_amount=loan_amount,
        interest_rate=interest_rate,
        tenure_years=tenure_years,
        optimal_emi=optimal_emi,
        total_interest=total_interest,
        created_at=datetime.utcnow()
    )

    db.add(loan_record)
    await db.commit()
    await db.refresh(loan_record)

    return loan_record
