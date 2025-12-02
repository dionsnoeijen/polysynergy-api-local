"""Authentication router for standalone mode.

Provides endpoints for user registration, login, password management, and 2FA.
Only active when SAAS_MODE=False.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import pyotp
import qrcode
from io import BytesIO
import base64

from core.settings import settings
from core.auth import get_auth_provider
from core.auth.standalone_provider import StandaloneAuthProvider
from db.session import get_db
from models import Account
from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    Enable2FAResponse,
    Verify2FARequest,
    MessageResponse,
)
from services.email.email_service import EmailService
from utils.get_current_account import get_current_account


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Helper Functions
# ============================================================================

def get_standalone_provider() -> StandaloneAuthProvider:
    """Get standalone auth provider (only works in standalone mode)."""
    if settings.SAAS_MODE:
        raise HTTPException(
            status_code=400,
            detail="Authentication endpoints are only available in standalone mode"
        )
    provider = get_auth_provider()
    if not isinstance(provider, StandaloneAuthProvider):
        raise HTTPException(status_code=500, detail="Invalid auth provider configuration")
    return provider


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate backup codes for 2FA recovery."""
    import secrets
    import string
    codes = []
    for _ in range(count):
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        codes.append(f"{code[:4]}-{code[4:]}")
    return codes


# ============================================================================
# Registration & Login
# ============================================================================

@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new user account (standalone mode only).

    Creates a new user with email verification required.
    """
    provider = get_standalone_provider()

    # Check if email already exists
    existing = db.query(Account).filter(Account.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate user ID
    external_user_id = provider.create_user(
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name
    )

    # Hash password
    password_hash = provider.hash_password(data.password)

    # Create account
    account = Account(
        external_user_id=external_user_id,
        auth_provider="standalone",
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        password_hash=password_hash,
        email_verified=False,
        active=True,  # Active but not verified
        single_user=False
    )
    db.add(account)
    db.commit()

    # Generate verification token
    verification_token = provider.create_verification_token(
        user_id=str(account.id),
        email=account.email
    )

    # Send verification email
    verification_url = f"{settings.PORTAL_URL}/verify-email?token={verification_token}"
    EmailService.send_email_verification(
        to=account.email,
        first_name=account.first_name,
        verification_url=verification_url,
        background_tasks=background_tasks
    )

    return MessageResponse(
        message="Registration successful. Please check your email to verify your account."
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login with email and password (standalone mode only).

    Returns access and refresh tokens on successful authentication.
    """
    provider = get_standalone_provider()

    # Find account
    account = db.query(Account).filter(Account.email == data.email).first()
    if not account or account.auth_provider != "standalone":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not account.password_hash or not provider.verify_password(data.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if account is active
    if not account.active:
        raise HTTPException(status_code=403, detail="Account is not active")

    # Check 2FA if enabled
    if account.totp_enabled:
        if not data.totp_code:
            raise HTTPException(
                status_code=401,
                detail="2FA code required",
                headers={"X-2FA-Required": "true"}
            )

        totp = pyotp.TOTP(account.totp_secret)
        if not totp.verify(data.totp_code, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    # Generate tokens
    access_token = provider.create_access_token(
        user_id=account.external_user_id,
        email=account.email
    )
    refresh_token = provider.create_refresh_token(
        user_id=account.external_user_id,
        email=account.email
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token (standalone mode only)."""
    provider = get_standalone_provider()

    # Validate refresh token
    try:
        decoded = provider.validate_token(data.refresh_token)
        if decoded.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = decoded.get("sub")
    email = decoded.get("email")

    # Verify account still exists
    account = db.query(Account).filter(Account.external_user_id == user_id).first()
    if not account or not account.active:
        raise HTTPException(status_code=401, detail="Account not found or inactive")

    # Generate new tokens
    access_token = provider.create_access_token(user_id=user_id, email=email)
    new_refresh_token = provider.create_refresh_token(user_id=user_id, email=email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    account: Account = Depends(get_current_account)
):
    """Logout (standalone mode).

    Note: Since we use stateless JWT tokens, logout is handled client-side
    by discarding the tokens. This endpoint exists for API consistency.
    """
    return MessageResponse(message="Logged out successfully")


# ============================================================================
# Email Verification
# ============================================================================

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """Verify email address using verification token."""
    provider = get_standalone_provider()

    # Validate token
    try:
        decoded = provider.validate_token(data.token)
        if decoded.get("type") != "verification":
            raise HTTPException(status_code=400, detail="Invalid token type")
    except HTTPException:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user_id = decoded.get("sub")

    # Update account
    account = db.query(Account).filter(Account.external_user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.email_verified:
        return MessageResponse(message="Email already verified")

    account.email_verified = True
    db.commit()

    return MessageResponse(message="Email verified successfully")


# ============================================================================
# Password Reset
# ============================================================================

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request password reset email (standalone mode only)."""
    provider = get_standalone_provider()

    # Find account (don't reveal if email exists or not)
    account = db.query(Account).filter(Account.email == data.email).first()
    if account and account.auth_provider == "standalone":
        # Generate reset token
        reset_token = provider.create_password_reset_token(
            user_id=account.external_user_id,
            email=account.email
        )

        # Send reset email
        reset_url = f"{settings.PORTAL_URL}/reset-password?token={reset_token}"
        EmailService.send_password_reset(
            to=account.email,
            first_name=account.first_name,
            reset_url=reset_url,
            background_tasks=background_tasks
        )

    # Always return success (don't reveal if email exists)
    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using reset token (standalone mode only)."""
    provider = get_standalone_provider()

    # Validate token
    try:
        decoded = provider.validate_token(data.token)
        if decoded.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
    except HTTPException:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user_id = decoded.get("sub")

    # Update password
    account = db.query(Account).filter(Account.external_user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.password_hash = provider.hash_password(data.new_password)
    db.commit()

    return MessageResponse(message="Password reset successfully")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """Change password for authenticated user (standalone mode only)."""
    provider = get_standalone_provider()

    if account.auth_provider != "standalone":
        raise HTTPException(
            status_code=400,
            detail="Password change only available for standalone accounts"
        )

    # Verify current password
    if not account.password_hash or not provider.verify_password(data.current_password, account.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Update password
    account.password_hash = provider.hash_password(data.new_password)
    db.commit()

    return MessageResponse(message="Password changed successfully")


# ============================================================================
# 2FA / TOTP
# ============================================================================

@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """Enable 2FA for account (standalone mode only).

    Returns TOTP secret and QR code for scanning with authenticator app.
    """
    get_standalone_provider()  # Verify standalone mode

    if account.auth_provider != "standalone":
        raise HTTPException(
            status_code=400,
            detail="2FA only available for standalone accounts"
        )

    if account.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    # Generate TOTP secret
    secret = pyotp.random_base32()
    account.totp_secret = secret
    db.commit()

    # Generate QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=account.email,
        issuer_name="PolySynergy"
    )

    qr = qrcode.make(totp_uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Generate backup codes
    backup_codes = generate_backup_codes()
    # TODO: Store hashed backup codes in database

    return Enable2FAResponse(
        secret=secret,
        qr_code=qr_base64,
        backup_codes=backup_codes
    )


@router.post("/2fa/verify", response_model=MessageResponse)
async def verify_2fa(
    data: Verify2FARequest,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """Verify and activate 2FA for account (standalone mode only)."""
    get_standalone_provider()  # Verify standalone mode

    if account.auth_provider != "standalone":
        raise HTTPException(status_code=400, detail="2FA only available for standalone accounts")

    if account.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    if not account.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not started. Call /2fa/enable first")

    # Verify TOTP code
    totp = pyotp.TOTP(account.totp_secret)
    if not totp.verify(data.totp_code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    # Activate 2FA
    account.totp_enabled = True
    db.commit()

    return MessageResponse(message="2FA enabled successfully")


@router.post("/2fa/disable", response_model=MessageResponse)
async def disable_2fa(
    data: ChangePasswordRequest,  # Reuse to require password confirmation
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    """Disable 2FA for account (standalone mode only).

    Requires password confirmation for security.
    """
    provider = get_standalone_provider()

    if account.auth_provider != "standalone":
        raise HTTPException(status_code=400, detail="2FA only available for standalone accounts")

    if not account.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    # Verify password
    if not account.password_hash or not provider.verify_password(data.current_password, account.password_hash):
        raise HTTPException(status_code=401, detail="Password is incorrect")

    # Disable 2FA
    account.totp_enabled = False
    account.totp_secret = None
    db.commit()

    return MessageResponse(message="2FA disabled successfully")
