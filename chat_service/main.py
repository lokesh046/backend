from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .orchestrator import FinancialOrchestrator
from .llm_client import LLMClient


from shared.database import get_db, engine, Base
import shared.models  # IMPORTANT: registers models

from shared.services.auth_routes import router as auth_router
from shared.services.auth import get_current_user
from shared.services.fire_service import save_fire_calculation
from shared.models.user import User
from shared.services.dashboard_routes import router as dashboard_router


# Database logic has been moved to main gateway


class ChatMessage(BaseModel):
    role: str
    content: str

from typing import Optional, List, Dict, Any
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None
    state: Optional[Dict[str, Any]] = None

router = APIRouter(tags=["Chat Agent"])

llm_client = LLMClient()
orchestrator = FinancialOrchestrator(llm_client)


@router.post("/chat-agent")
async def chat_agent(
    data: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get JWT token from cookie or header
    auth_token = None
    
    # Try to get from cookie
    auth_token = request.cookies.get("access_token")
    
    # If not in cookie, try header
    if not auth_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.replace("Bearer ", "")
    
    # Pass auth token to orchestrator for internal service calls
    print(f"DEBUG: Handling chat request: {data.message}")
    
    history_dict = [h.dict() for h in data.history] if data.history else None
    
    result = await orchestrator.handle_request(
        message=data.message, 
        auth_token=auth_token,
        history=history_dict,
        previous_state_dict=data.state
    )
    print(f"DEBUG: Orchestrator Result: {result}")

    # Save FIRE result if exists and is valid
    fire_year = result.get("state", {}).get("fire_year")
    if result.get("state", {}).get("fire_number") is not None and not isinstance(fire_year, str):
        try:
            await save_fire_calculation(
                db=db,
                user_id=current_user.id,
                monthly_income=result["state"].get("monthly_income"),
                living_expense=result["state"].get("living_expense"),
                current_savings=result["state"].get("current_savings"),
                fire_number=result["state"].get("fire_number"),
                fire_year=fire_year,
                final_wealth=result["state"].get("final_wealth")
            )
        except Exception as e:
            print(f"Error saving chat FIRE result: {e}")

    return result



@router.get("/health/db")
async def db_health(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(text("SELECT 1"))
    return {"database": "connected", "result": result.scalar()}