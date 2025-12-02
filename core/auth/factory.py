"""Factory for creating authentication providers based on SAAS_MODE."""

from core.settings import settings
from .base import AuthProvider
from .cognito_provider import CognitoAuthProvider
from .standalone_provider import StandaloneAuthProvider


_provider_instance: AuthProvider | None = None


def get_auth_provider() -> AuthProvider:
    """Get the configured authentication provider.

    Returns the appropriate provider based on SAAS_MODE setting:
    - SAAS_MODE=True: CognitoAuthProvider (AWS Cognito)
    - SAAS_MODE=False: StandaloneAuthProvider (local auth)

    Returns:
        AuthProvider instance

    Raises:
        ValueError: If required settings are missing for the selected mode
    """
    global _provider_instance

    # Create singleton instance
    if _provider_instance is None:
        if settings.SAAS_MODE:
            # Validate Cognito settings
            if not settings.COGNITO_AWS_REGION or not settings.COGNITO_USER_POOL_ID or not settings.COGNITO_APP_CLIENT_ID:
                raise ValueError(
                    "SAAS_MODE=True requires COGNITO_AWS_REGION, "
                    "COGNITO_USER_POOL_ID, and COGNITO_APP_CLIENT_ID to be set"
                )
            _provider_instance = CognitoAuthProvider()
        else:
            # Validate standalone settings
            if not settings.JWT_SECRET_KEY:
                raise ValueError(
                    "SAAS_MODE=False requires JWT_SECRET_KEY to be set"
                )
            _provider_instance = StandaloneAuthProvider()

    return _provider_instance


def reset_auth_provider():
    """Reset the provider instance (useful for testing)."""
    global _provider_instance
    _provider_instance = None
