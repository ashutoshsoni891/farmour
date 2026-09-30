import uuid
from datetime import timedelta

import jwt
import pytest

from app.core import session_tokens as st


def test_roundtrip() -> None:
    uid = uuid.uuid4()
    token = st.issue(uid, 3, timedelta(minutes=5))
    assert st.is_session_token(token)
    claims = st.verify(token)
    assert claims.user_id == uid
    assert claims.session_version == 3


def test_expired_token_rejected() -> None:
    token = st.issue(uuid.uuid4(), 1, timedelta(seconds=-1))
    with pytest.raises(st.SessionTokenError):
        st.verify(token)


def test_tampered_token_rejected() -> None:
    token = st.issue(uuid.uuid4(), 1, timedelta(minutes=5))
    forged = jwt.encode(
        {**jwt.decode(token, options={"verify_signature": False}), "sv": 99},
        "another-secret-" + "y" * 40,
        algorithm="HS256",
    )
    with pytest.raises(st.SessionTokenError):
        st.verify(forged)


def test_wrong_audience_rejected() -> None:
    secret = st._secret()
    token = jwt.encode(
        {"iss": st.ISSUER, "aud": "other", "sub": str(uuid.uuid4()), "sv": 1, "exp": 9999999999},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(st.SessionTokenError):
        st.verify(token)


def test_garbage_is_not_session_token() -> None:
    assert not st.is_session_token("not-a-jwt")
