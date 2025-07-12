from fastapi import Request, HTTPException, status, Depends
from jwt import PyJWKClient, decode, ExpiredSignatureError, InvalidTokenError
from cachetools import TTLCache
from app.settings import COGNITO_USER_POOL, COGNITO_AWS_REGION, COGNITO_AUDIENCE
from app.models import Account

_jwks_cache = TTLCache(maxsize=1, ttl=60 * 60 * 24)  # 24 uur

def get_jwks_client() -> PyJWKClient:
    if "jwks_client" not in _jwks_cache:
        keys_url = f"https://cognito-idp.{COGNITO_AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL}/.well-known/jwks.json"
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
            audience=COGNITO_AUDIENCE,
            options={"verify_exp": True},
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def get_current_account(request: Request) -> Account:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.replace("Bearer ", "")
    decoded = validate_token(token)
    sub = decoded.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    account = Account.objects.filter(cognito_id=sub).first()  # <-- vervangen door SQLAlchemy bij migratie
    if not account:
        raise HTTPException(status_code=401, detail="Account not found")

    return account