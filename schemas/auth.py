"""Authentication schemas for request/response validation."""

from pydantic import BaseModel, EmailStr
from typing import Optional


# ============================================================================
# Request Schemas
# ============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class Verify2FARequest(BaseModel):
    totp_code: str


# ============================================================================
# Response Schemas
# ============================================================================

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class Enable2FAResponse(BaseModel):
    secret: str
    qr_code: str  # Base64 encoded PNG
    backup_codes: list[str]


class MessageResponse(BaseModel):
    message: str
