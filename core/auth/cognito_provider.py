"""Cognito authentication provider for SAAS mode."""

import boto3
from typing import Dict, Any, Optional
from fastapi import HTTPException
from jwt import PyJWKClient, decode, ExpiredSignatureError, InvalidTokenError
from cachetools import TTLCache

from core.settings import settings
from .base import AuthProvider


class CognitoAuthProvider(AuthProvider):
    """AWS Cognito authentication provider."""

    def __init__(self):
        self._jwks_cache = TTLCache(maxsize=1, ttl=60 * 60 * 24)  # 24 hour cache
        self._cognito_client = None

    def _get_jwks_client(self) -> PyJWKClient:
        """Get or create cached JWKS client."""
        if "jwks_client" not in self._jwks_cache:
            keys_url = (
                f"https://cognito-idp.{settings.COGNITO_AWS_REGION}.amazonaws.com/"
                f"{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
            )
            self._jwks_cache["jwks_client"] = PyJWKClient(keys_url)
        return self._jwks_cache["jwks_client"]

    def _get_cognito_client(self):
        """Get or create Cognito client."""
        if not self._cognito_client:
            self._cognito_client = boto3.client(
                service_name='cognito-idp',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        return self._cognito_client

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate Cognito JWT token.

        Args:
            token: JWT token from Cognito

        Returns:
            Dict containing decoded token claims

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            jwks_client = self._get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            return decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.COGNITO_APP_CLIENT_ID,
                options={"verify_exp": True},
            )
        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        temporary_password: Optional[str] = None,
        **kwargs
    ) -> str:
        """Create user in Cognito.

        Args:
            email: User's email
            first_name: User's first name
            last_name: User's last name
            temporary_password: Temporary password (for invite flow)
            **kwargs: Additional Cognito attributes

        Returns:
            Cognito user ID (sub)
        """
        client = self._get_cognito_client()

        user_attributes = [
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": "true"},
        ]

        if first_name:
            user_attributes.append({"Name": "given_name", "Value": first_name})
        if last_name:
            user_attributes.append({"Name": "family_name", "Value": last_name})

        # Add any custom attributes from kwargs
        for key, value in kwargs.items():
            if key.startswith("custom:"):
                user_attributes.append({"Name": key, "Value": str(value)})

        create_params = {
            "UserPoolId": settings.COGNITO_USER_POOL_ID,
            "Username": email,
            "UserAttributes": user_attributes,
            "MessageAction": "SUPPRESS",  # Don't send default Cognito email
        }

        if temporary_password:
            create_params["TemporaryPassword"] = temporary_password

        response = client.admin_create_user(**create_params)
        return response["User"]["Username"]  # This is the Cognito user ID

    def update_user(
        self,
        external_user_id: str,
        **attributes
    ) -> None:
        """Update Cognito user attributes.

        Args:
            external_user_id: Cognito user ID (username/email)
            **attributes: Attributes to update (first_name, last_name, etc.)
        """
        client = self._get_cognito_client()

        cognito_attrs = []

        if "first_name" in attributes and attributes["first_name"]:
            cognito_attrs.append({"Name": "given_name", "Value": attributes["first_name"]})
        if "last_name" in attributes and attributes["last_name"]:
            cognito_attrs.append({"Name": "family_name", "Value": attributes["last_name"]})
        if "email" in attributes and attributes["email"]:
            cognito_attrs.append({"Name": "email", "Value": attributes["email"]})

        # Add custom attributes
        for key, value in attributes.items():
            if key.startswith("custom:"):
                cognito_attrs.append({"Name": key, "Value": str(value)})

        if cognito_attrs:
            client.admin_update_user_attributes(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=external_user_id,
                UserAttributes=cognito_attrs
            )

    def delete_user(self, external_user_id: str) -> None:
        """Delete user from Cognito.

        Args:
            external_user_id: Cognito user ID (username/email)
        """
        client = self._get_cognito_client()
        client.admin_delete_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=external_user_id,
        )

    def set_temporary_password(
        self,
        external_user_id: str,
        password: str
    ) -> None:
        """Set temporary password in Cognito.

        Args:
            external_user_id: Cognito user ID (username/email)
            password: Temporary password
        """
        client = self._get_cognito_client()
        client.admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=external_user_id,
            Password=password,
            Permanent=False,
        )

    def send_password_reset_email(self, email: str) -> None:
        """Trigger Cognito forgot password flow.

        Args:
            email: User's email address
        """
        client = self._get_cognito_client()
        client.forgot_password(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            Username=email,
        )
