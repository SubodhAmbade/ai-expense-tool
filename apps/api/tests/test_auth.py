from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import app.auth as auth

ISSUER = "https://demo.supabase.co/auth/v1"
KEY = ec.generate_private_key(ec.SECP256R1())  # stands in for the project's signing key


class FakeJwks:
    def get_signing_key_from_jwt(self, _token):
        return type("Key", (), {"key": KEY.public_key()})


@pytest.fixture(autouse=True)
def project(monkeypatch):
    monkeypatch.setattr(auth, "_issuer", lambda: ISSUER)
    monkeypatch.setattr(auth, "_jwks", lambda: FakeJwks())


def token(key=KEY, **changes) -> HTTPAuthorizationCredentials:
    claims = {
        "sub": "user-a",
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    } | changes
    return HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=jwt.encode(claims, key, "ES256")
    )


def test_valid_token_gives_the_user_id() -> None:
    assert auth.current_user(token()) == "user-a"


@pytest.mark.parametrize(
    "credentials",
    [
        None,  # no Authorization header
        token(exp=datetime.now(UTC) - timedelta(minutes=1)),  # expired
        token(aud="anon"),  # not a signed-in user's token
        token(iss="https://other.supabase.co/auth/v1"),  # another project's token
        token(key=ec.generate_private_key(ec.SECP256R1())),  # signed by someone else
    ],
)
def test_bad_tokens_are_rejected(credentials) -> None:
    with pytest.raises(HTTPException) as err:
        auth.current_user(credentials)
    assert err.value.status_code == 401
