"""
Security and Health Endpoint Tests.
"""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.main import app


def test_password_hashing():
    pwd = "SecretTradingPassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_tokens():
    user_id = uuid4()
    access_tok = create_access_token(user_id)
    assert isinstance(access_tok, str)

    payload = decode_token(access_tok)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"

    refresh_tok = create_refresh_token(user_id)
    assert isinstance(refresh_tok, str)
    ref_payload = decode_token(refresh_tok)
    assert ref_payload is not None
    assert ref_payload["sub"] == str(user_id)
    assert ref_payload["type"] == "refresh"


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "TradeGear" in data["app"]
