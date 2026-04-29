from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import secrets
from datetime import datetime, timedelta

from shared.database import get_db
from shared.models.user import User, EmailVerificationOTP, PasswordResetToken
from shared.services.auth import create_access_token, verify_password, hash_password
from shared.services.email_service import send_email_async

from pydantic import BaseModel, EmailStr, field_validator
import re

router = APIRouter()

# --- Schemas ---
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format.")
        return v

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class ResendOTPRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# --- Helpers ---
def generate_otp() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(6))

# -------------------------
# Register & OTP Verification
# -------------------------
@router.post("/register")
async def register(data: RegisterRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where((User.email == data.email) | (User.username == data.username)))
    existing_users = result.scalars().all()

    for user in existing_users:
        if user.email == data.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        if user.username == data.username:
            raise HTTPException(status_code=400, detail="Username already exists.")

    new_user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        role="user",
        is_active=True,
        is_verified=False, # Now False by default
    )
    db.add(new_user)
    await db.flush() # flush to get user ID

    # Generate and save OTP
    otp_code = generate_otp()
    otp_record = EmailVerificationOTP(
        user_id=new_user.id,
        otp_hash=hash_password(otp_code), # Hashing OTP
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(otp_record)
    await db.commit()

    # Send Email
    html_content = f"<h3>Welcome to Wealth To FIRE!</h3><p>Your verification code is: <strong style='font-size:24px;'>{otp_code}</strong></p><p>This code expires in 10 minutes.</p>"
    background_tasks.add_task(send_email_async, new_user.email, "Verify Your Email", html_content)

    return {"message": "User created. Check your email for the verification code.", "email": data.email}


@router.post("/verify-email")
async def verify_email(data: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    if user.is_verified:
        return {"message": "User is already verified"}

    result_otp = await db.execute(select(EmailVerificationOTP).where(EmailVerificationOTP.user_id == user.id))
    otp_record = result_otp.scalar_one_or_none()

    if not otp_record:
        raise HTTPException(status_code=400, detail="No active OTP found. Please request a new one.")

    if datetime.utcnow() > otp_record.expires_at:
        await db.delete(otp_record)
        await db.commit()
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    if otp_record.attempts >= 3:
        await db.delete(otp_record)
        await db.commit()
        raise HTTPException(status_code=400, detail="Maximum attempts reached. Please request a new OTP.")

    if not verify_password(data.otp, otp_record.otp_hash):
        otp_record.attempts += 1
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    # Success!
    user.is_verified = True
    await db.delete(otp_record)
    await db.commit()
    
    return {"message": "Email verified successfully!"}


@router.post("/resend-otp")
async def resend_otp(data: ResendOTPRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        return {"message": "If that email is registered, a new OTP has been sent."} # Prevent email enumeration
        
    if user.is_verified:
        raise HTTPException(status_code=400, detail="User is already verified")

    # Delete existing OTPs
    await db.execute(delete(EmailVerificationOTP).where(EmailVerificationOTP.user_id == user.id))
    
    # Generate new OTP
    otp_code = generate_otp()
    otp_record = EmailVerificationOTP(
        user_id=user.id,
        otp_hash=hash_password(otp_code),
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(otp_record)
    await db.commit()

    # Send Email
    html_content = f"<h3>Wealth To FIRE</h3><p>Your new verification code is: <strong style='font-size:24px;'>{otp_code}</strong></p><p>This code expires in 10 minutes.</p>"
    background_tasks.add_task(send_email_async, user.email, "Your New Verification Code", html_content)

    return {"message": "A new OTP has been sent."}


# -------------------------
# Login (OAuth2 Compatible)
# -------------------------
@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email address first.")

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "username": user.username, "role": user.role}
    )

    response.set_cookie(
        key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600 * 24 * 7
    )

    return {
        "access_token": access_token, "token_type": "bearer", "user_id": str(user.id),
        "email": user.email, "username": user.username, "role": user.role, "message": "Login successful!"
    }


# -------------------------
# Forgot / Reset Password
# -------------------------
@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    # We always return success to prevent email enumeration attacks
    if not user:
        return {"message": "If an account exists, a password reset link has been sent."}

    # Clean up old tokens
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    
    # Generate token
    raw_token = secrets.token_urlsafe(32)
    token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    db.add(token_record)
    await db.commit()

    # Send Email with token format user.id:raw_token to prevent bcrypt DoS
    reset_link = f"http://localhost:5173/reset-password?token={user.id}:{raw_token}"
    html_content = f"<h3>Reset Your Password</h3><p>Click the link below to reset your password. This link is valid for 15 minutes.</p><p><a href='{reset_link}'>{reset_link}</a></p>"
    background_tasks.add_task(send_email_async, user.email, "Reset Your Password", html_content)

    return {"message": "If an account exists, a password reset link has been sent."}

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        if ":" not in data.token:
            raise ValueError()
        user_id_str, raw_token = data.token.split(":", 1)
    except:
        raise HTTPException(status_code=400, detail="Invalid token format.")

    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id == user_id_str))
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    if datetime.utcnow() > token_record.expires_at:
        await db.delete(token_record)
        await db.commit()
        raise HTTPException(status_code=400, detail="Token has expired.")

    if not verify_password(raw_token, token_record.token_hash):
        raise HTTPException(status_code=400, detail="Invalid reset token.")

    # Update Password
    result_user = await db.execute(select(User).where(User.id == user_id_str))
    user = result_user.scalar_one()
    user.password_hash = hash_password(data.new_password)
    
    await db.delete(token_record)
    await db.commit()

    return {"message": "Password has been successfully reset."}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}
