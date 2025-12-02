"""Standalone authentication provider for self-hosted mode."""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException
from passlib.context import CryptContext
from uuid import uuid4

from core.settings import settings
from .base import AuthProvider


class StandaloneAuthProvider(AuthProvider):
    """Standalone authentication provider using FastAPI + JWT."""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token.

        Args:
            token: JWT token string

        Returns:
            Dict containing token claims

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    def create_access_token(
        self,
        user_id: str,
        email: str,
        expires_minutes: Optional[int] = None
    ) -> str:
        """Create JWT access token.

        Args:
            user_id: User's ID
            email: User's email
            expires_minutes: Token expiration in minutes (default from settings)

        Returns:
            JWT token string
        """
        if expires_minutes is None:
            expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

        payload = {
            "sub": user_id,  # Standard JWT claim for user ID
            "email": email,
            "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
            "iat": datetime.utcnow(),
            "type": "access"
        }

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_refresh_token(
        self,
        user_id: str,
        email: str,
        expires_days: Optional[int] = None
    ) -> str:
        """Create JWT refresh token.

        Args:
            user_id: User's ID
            email: User's email
            expires_days: Token expiration in days (default from settings)

        Returns:
            JWT token string
        """
        if expires_days is None:
            expires_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

        payload = {
            "sub": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(days=expires_days),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_verification_token(self, user_id: str, email: str) -> str:
        """Create email verification token.

        Args:
            user_id: User's ID
            email: User's email

        Returns:
            JWT token string (valid for 24 hours)
        """
        payload = {
            "sub": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow(),
            "type": "verification"
        }

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_password_reset_token(self, user_id: str, email: str) -> str:
        """Create password reset token.

        Args:
            user_id: User's ID
            email: User's email

        Returns:
            JWT token string (valid for 1 hour)
        """
        payload = {
            "sub": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "password_reset"
        }

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        temporary_password: Optional[str] = None,
        **kwargs
    ) -> str:
        """Create user in standalone mode.

        Note: This method only generates a user ID. The actual database
        insertion happens in the service layer.

        Args:
            email: User's email
            first_name: User's first name
            last_name: User's last name
            temporary_password: Temporary password (for invite flow)
            **kwargs: Additional parameters (ignored in standalone mode)

        Returns:
            Generated user ID
        """
        # In standalone mode, we generate a UUID for the user
        # The Account record creation happens in the service layer
        return str(uuid4())

    def update_user(
        self,
        external_user_id: str,
        **attributes
    ) -> None:
        """Update user in standalone mode.

        Note: In standalone mode, all user data is in the database,
        so this is a no-op. Updates happen in the service layer.

        Args:
            external_user_id: User's ID
            **attributes: Attributes to update
        """
        # No-op: all user data is in our database
        pass

    def delete_user(self, external_user_id: str) -> None:
        """Delete user in standalone mode.

        Note: In standalone mode, deletion happens in the database,
        so this is a no-op.

        Args:
            external_user_id: User's ID
        """
        # No-op: deletion happens in the database
        pass

    def set_temporary_password(
        self,
        external_user_id: str,
        password: str
    ) -> None:
        """Set temporary password in standalone mode.

        Note: Password updates happen in the database,
        so this is a no-op. The service layer handles this.

        Args:
            external_user_id: User's ID
            password: Temporary password
        """
        # No-op: password is set in the database by service layer
        pass

    def send_password_reset_email(self, email: str) -> None:
        """Send password reset email.

        Note: Email sending is handled by EmailService in the service layer.
        This method is here for interface compliance but doesn't need
        to do anything.

        Args:
            email: User's email address
        """
        # No-op: email sending happens in service/endpoint layer
        pass
