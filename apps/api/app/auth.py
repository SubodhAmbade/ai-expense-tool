"""Who is asking: verifies the Supabase sign-in token sent with every receipts request.

Tokens are signed by Supabase with a private key; we check them against the project's public
keys (JWKS). The key set is cached for 5 minutes, so a key revoked in Supabase stops working soon
after, and no secret is needed. Projects still on the legacy shared secret (HS256) aren't
supported: switch to asymmetric JWT keys in Supabase.
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
    return jwt.PyJWKClient(f"{_issuer()}/.well-known/jwks.json")  # key set cached 5 minutes


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
            token,
            key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=_issuer(),
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:  # bad signature, expired, wrong project or audience, missing claim
        raise unauthorised from None
    user = claims["sub"]
    if not isinstance(user, str) or not user:  # every query is filtered by it
        raise unauthorised
    return user


UserDep = Annotated[str, Depends(current_user)]
