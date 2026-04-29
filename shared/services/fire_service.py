import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import FireCalculation


async def save_fire_calculation(
    db: AsyncSession,
    user_id: uuid.UUID,
    monthly_income: float,
    living_expense: float,
    current_savings: float,
    fire_number: float,
    fire_year: float,
    final_wealth: float,
    scenario_name: str = "Primary Goal"
):
    fire_record = FireCalculation(
        id=uuid.uuid4(),
        user_id=user_id,
        monthly_income=monthly_income,
        living_expense=living_expense,
        current_savings=current_savings,
        fire_number=fire_number,
        fire_year=fire_year,
        final_wealth=final_wealth,
        scenario_name=scenario_name,
        created_at=datetime.utcnow()
    )

    db.add(fire_record)
    await db.commit()
    await db.refresh(fire_record)

    return fire_record