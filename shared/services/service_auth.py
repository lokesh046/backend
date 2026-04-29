"""
Shared Authentication Middleware for Microservices
Can be used by all services (fire, health, loan, explain)
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Any
from functools import wraps

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_change_me_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
security = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    """Parsed token data"""
    user_id: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    tenant_id: Optional[str] = None
    exp: Optional[datetime] = None


class CurrentUser(BaseModel):
    """Current authenticated user"""
    id: str
    username: str = ""
    email: str
    role: str = "user"
    tenant_id: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    tenant_id: Optional[str] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    expire = datetime.utcnow() + (
        expires_delta if expires_delta 
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    to_encode.update({
        "exp": expire,
        "tenant_id": tenant_id
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        user_id: Optional[str] = payload.get("sub")
        email: Optional[str] = payload.get("email")
        username: Optional[str] = payload.get("username", "")
        role: Optional[str] = payload.get("role", "user")
        tenant_id: Optional[str] = payload.get("tenant_id")
        exp: Optional[datetime] = payload.get("exp")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        return TokenData(
            user_id=user_id,
            email=email,
            username=username,
            role=role,
            tenant_id=tenant_id,
            exp=exp
        )
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    Dependency to get current authenticated user.
    Use this in any FastAPI endpoint to require authentication.
    
    Usage:
        @app.post("/endpoint")
        async def endpoint(user: CurrentUser = Depends(get_current_user)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = decode_token(credentials.credentials)
    
    return CurrentUser(
        id=token_data.user_id,
        email=token_data.email or "",
        username=token_data.username or "",
        role=token_data.role,
        tenant_id=token_data.tenant_id
    )


async def get_current_active_user(
    user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """Require user to be active"""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return user


async def get_current_verified_user(
    user: CurrentUser = Depends(get_current_active_user)
) -> CurrentUser:
    """Require user to be verified"""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User email is not verified"
        )
    return user


def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @app.get("/admin")
        async def admin_endpoint(user: CurrentUser = Depends(require_role("admin", "super_admin"))):
            ...
    """
    async def role_checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return user
    
    return role_checker


def require_verified():
    """Dependency that requires verified email"""
    async def verifier(user: CurrentUser = Depends(get_current_verified_user)) -> CurrentUser:
        return user
    return verifier


class RateLimiter:
    """Simple in-memory rate limiter"""
    _requests: dict = {}
    
    @classmethod
    async def check_rate_limit(
        cls,
        identifier: str,
        max_requests: int = 100,
        window_seconds: int = 60
    ) -> bool:
        """Check if request is within rate limit"""
        from time import time
        
        now = time()
        key = f"{identifier}"
        
        if key not in cls._requests:
            cls._requests[key] = []
        
        cls._requests[key] = [
            ts for ts in cls._requests[key]
            if now - ts < window_seconds
        ]
        
        if len(cls._requests[key]) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        cls._requests[key].append(now)
        return True


async def get_service_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    Service-to-service authentication.
    Accepts either user JWT or service API key.
    """
    if credentials:
        return await get_current_user(credentials)
    
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return CurrentUser(
            id="service",
            email="service@internal",
            role="service"
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )
