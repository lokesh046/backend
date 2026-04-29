import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import HealthScore


async def save_health_score(
    db: AsyncSession,
    user_id: uuid.UUID,
    score: float,
    fire_number: float,
    debt_ratio: float,
    savings_ratio: float
):
    health_record = HealthScore(
        id=uuid.uuid4(),
        user_id=user_id,
        score=score,
        fire_number=fire_number,
        debt_ratio=debt_ratio,
        savings_ratio=savings_ratio,
        created_at=datetime.utcnow()
    )

    db.add(health_record)
    await db.commit()
    await db.refresh(health_record)

    return health_record
