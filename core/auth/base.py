"""Abstract base class for authentication providers."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class AuthProvider(ABC):
    """Abstract base class for authentication providers.

    This interface allows switching between different auth backends
    (Cognito for SAAS mode, standalone for self-hosted).
    """

    @abstractmethod
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and return decoded claims.

        Args:
            token: JWT token string

        Returns:
            Dict containing token claims (must include 'sub' for user ID)

        Raises:
            HTTPException: If token is invalid or expired
        """
        pass

    @abstractmethod
    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        temporary_password: Optional[str] = None,
        **kwargs
    ) -> str:
        """Create a new user in the auth provider.

        Args:
            email: User's email address
            first_name: User's first name
            last_name: User's last name
            temporary_password: Optional temporary password for invite flow
            **kwargs: Additional provider-specific parameters

        Returns:
            External user ID (cognito_id or standalone user_id)

        Raises:
            Exception: If user creation fails
        """
        pass

    @abstractmethod
    def update_user(
        self,
        external_user_id: str,
        **attributes
    ) -> None:
        """Update user attributes in the auth provider.

        Args:
            external_user_id: User's external ID
            **attributes: Attributes to update (e.g., email, name, etc.)

        Raises:
            Exception: If update fails
        """
        pass

    @abstractmethod
    def delete_user(self, external_user_id: str) -> None:
        """Delete user from the auth provider.

        Args:
            external_user_id: User's external ID

        Raises:
            Exception: If deletion fails
        """
        pass

    @abstractmethod
    def set_temporary_password(
        self,
        external_user_id: str,
        password: str
    ) -> None:
        """Set a temporary password for user (invite flow).

        Args:
            external_user_id: User's external ID
            password: Temporary password

        Raises:
            Exception: If operation fails
        """
        pass

    @abstractmethod
    def send_password_reset_email(self, email: str) -> None:
        """Send password reset email to user.

        Args:
            email: User's email address

        Raises:
            Exception: If operation fails
        """
        pass
