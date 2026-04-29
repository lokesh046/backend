from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Literal, Optional
import os
import shutil

from .pipeline.retrieval import retrieve
from .pipeline.prompt_builder import build_prompt
from .pipeline.ingestion import ingest_file
from .pipeline.vectordb import index
from .pipeline.llm_client import generate_explanation
from shared.services.service_auth import get_current_user, CurrentUser

router = APIRouter(tags=["Explain Service"])


ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "super_secret_key_change_me")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ExplainRequest(BaseModel):
    context_type: Literal["loan_fire_strategy"]
    current_fire_year: int
    optimized_fire_year: int
    recommended_emi: float
    strategy_recommendation: str
    financial_health_score: float


class ExplainResponse(BaseModel):
    summary: str
    reasoning_points: list[str]
    risk_note: str
    sources: list[str]
    confidence_score: float

class AskRequest(BaseModel):
    query: str

class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence_score: float


def verify_admin(api_key: str) -> bool:
    """Verify admin API key"""
    if api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key"
        )
    return True


def verify_user_or_admin(
    authorization: Optional[str] = Header(None),
    api_key: Optional[str] = Header(None)
) -> CurrentUser:
    """
    Verify either user JWT or admin API key.
    For /explain-strategy: requires user authentication
    For /admin/*: requires admin API key
    """
    if api_key:
        verify_admin(api_key)
        return CurrentUser(
            id="admin",
            email="admin@system",
            role="admin"
        )
    
    if authorization:
        token = authorization.replace("Bearer ", "")
        from shared.services.service_auth import decode_token
        token_data = decode_token(token)
        return CurrentUser(
            id=token_data.user_id,
            email=token_data.email or "",
            role=token_data.role
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


@router.post("/explain-strategy", response_model=ExplainResponse)
async def explain_strategy(
    data: ExplainRequest,
    user: CurrentUser = Depends(verify_user_or_admin)
):
    """
    Generate AI explanation for financial strategy.
    Requires authentication (JWT or admin API key).
    """
    if not user.is_active and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    try:
        query = f"{data.strategy_recommendation} fire timeline debt impact"

        context, sources, confidence = retrieve(query)

        prompt = build_prompt(context, data)

        explanation_structured = await generate_explanation(prompt)

        return {
            **explanation_structured,
            "sources": sources,
            "confidence_score": confidence
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating explanation: {str(e)}"
        )

@router.post("/ask", response_model=AskResponse)
async def ask_question(
    data: AskRequest,
    user: CurrentUser = Depends(verify_user_or_admin)
):
    """
    RAG-powered Financial Second Brain Q&A.
    """
    if not user.is_active and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    try:
        from .pipeline.prompt_builder import build_qa_prompt
        from .pipeline.llm_client import generate_raw_text
        
        context, sources, confidence = retrieve(data.query)
        prompt = build_qa_prompt(context, data.query)
        answer = await generate_raw_text(prompt)

        print("\n=== RAG PROMPT ===")
        print(prompt)
        print("==================\n")

        return {
            "answer": answer,
            "sources": sources,
            "confidence_score": confidence
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}"
        )


@router.post("/admin/upload")
async def admin_upload(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(verify_user_or_admin)
):
    """
    Admin endpoint to upload knowledge base documents.
    Requires admin privileges.
    """
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = ingest_file(file_path, file.filename)

    return {
        "status": "Knowledge uploaded",
        "details": result
    }


@router.delete("/admin/delete")
async def admin_delete(
    source: str,
    user: CurrentUser = Depends(verify_user_or_admin)
):
    """
    Admin endpoint to delete knowledge base documents.
    Requires admin privileges.
    """
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    index.delete(filter={"source": source})

    return {"status": "Deleted successfully"}


@router.get("/health")
def health_check():
    """Public health check endpoint"""
    return {"status": "healthy", "service": "explain_service"}


@router.get("/protected")
def protected_endpoint(user: CurrentUser = Depends(verify_user_or_admin)):
    """Test endpoint to verify authentication"""
    return {
        "message": "You are authenticated!",
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    }
