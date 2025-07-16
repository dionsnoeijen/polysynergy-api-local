from uuid import UUID

from fastapi import Request, HTTPException, Depends, Query, Path
from jwt import PyJWKClient, decode, ExpiredSignatureError, InvalidTokenError
from cachetools import TTLCache
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.settings import settings
from db.session import get_db
from models import Account, Membership, Project

_jwks_cache = TTLCache(maxsize=1, ttl=60 * 60 * 24)

def get_jwks_client() -> PyJWKClient:
    if "jwks_client" not in _jwks_cache:
        keys_url = f"https://cognito-idp.{settings.COGNITO_AWS_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
        _jwks_cache["jwks_client"] = PyJWKClient(keys_url)
    return _jwks_cache["jwks_client"]


def validate_token(token: str) -> dict:
    try:
        jwks_client = get_jwks_client()
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


def get_current_account(
    request: Request,
    db: Session = Depends(get_db)
) -> Account:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.replace("Bearer ", "")
    decoded = validate_token(token)
    sub = decoded.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    account = db.query(Account).filter(Account.cognito_id == sub).first()
    if not account:
        raise HTTPException(status_code=401, detail="Account not found")

    return account

def get_project_id_from_query(
    project_id: UUID = Query(...)
) -> UUID:
    return project_id

def get_project_or_403(
    project_id: UUID = Depends(get_project_id_from_query),
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> Project:
    stmt = (
        select(Project)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(Project.id == project_id)
        .where(Membership.account_id == account.id)
    )
    project = db.scalar(stmt)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    return project