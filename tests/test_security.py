"""Unit tests for security primitives."""

from __future__ import annotations

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed.startswith("pbkdf2$")
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_hashes_are_salted() -> None:
    assert hash_password("same") != hash_password("same")


def test_verify_password_malformed_hash() -> None:
    assert not verify_password("anything", "not-a-real-hash")
    assert not verify_password("anything", "")


def test_jwt_roundtrip() -> None:
    token = create_access_token(subject="user-123", role="admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"


def test_jwt_invalid_token_rejected() -> None:
    with pytest.raises(AuthenticationError):
        decode_access_token("not.a.token")
