"""Who is asking: verifies the Supabase sign-in token sent with every receipts request.

Tokens are signed by Supabase with a private key; we check them against the project's public
keys (JWKS), fetched once and cached. No secret is needed, and nothing is called per request.
"""

from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

bearer = HTTPBearer(auto_error=False)  # we raise our own 401 with a clearer message


@lru_cache
def _issuer() -> str:
    return f"{get_settings().supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def _jwks() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{_issuer()}/.well-known/jwks.json", cache_keys=True)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    """The signed-in user's id, or 401."""
    unauthorised = HTTPException(401, "Sign in again", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorised
    token = credentials.credentials
    try:
        key = _jwks().get_signing_key_from_jwt(token).key
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, "Can't reach Supabase to check the sign-in") from None
    except jwt.PyJWTError:
        raise unauthorised from None
    try:
        claims = jwt.decode(
            token, key, algorithms=["ES256", "RS256"], audience="authenticated", issuer=_issuer()
        )
    except jwt.PyJWTError:  # bad signature, expired, wrong project or audience
        raise unauthorised from None
    return claims["sub"]


UserDep = Annotated[str, Depends(current_user)]
