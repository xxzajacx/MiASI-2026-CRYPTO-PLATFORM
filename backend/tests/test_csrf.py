"""Tests for CSRF middleware and utilities."""
import os
import json
import pytest
from starlette.requests import Request
from starlette.responses import Response
from app.core.csrf import (
    generate_csrf_token,
    validate_csrf_token,
    CSRFMiddleware,
    set_csrf_cookie,
    unset_csrf_cookie,
    CSRF_COOKIE_NAME,
    CSRF_TOKEN_HEADER
)


class DummyApp:
    pass


def test_generate_csrf_token():
    """Test token generation returns a non-empty string."""
    token = generate_csrf_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_validate_csrf_token_no_cookie():
    """Test verification fails if cookie is missing."""
    scope = {
        "type": "http",
        "headers": [
            (CSRF_TOKEN_HEADER.lower().encode(), b"some_token"),
        ],
    }
    request = Request(scope)
    assert validate_csrf_token(request) is False


def test_validate_csrf_token_no_header():
    """Test verification fails if header is missing."""
    scope = {
        "type": "http",
        "headers": [
            (b"cookie", f"{CSRF_COOKIE_NAME}=some_token".encode()),
        ],
    }
    request = Request(scope)
    assert validate_csrf_token(request) is False


def test_validate_csrf_token_mismatch():
    """Test verification fails if cookie and header tokens do not match."""
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    scope = {
        "type": "http",
        "headers": [
            (b"cookie", f"{CSRF_COOKIE_NAME}={token1}".encode()),
            (CSRF_TOKEN_HEADER.lower().encode(), token2.encode()),
        ],
    }
    request = Request(scope)
    assert validate_csrf_token(request) is False


def test_validate_csrf_token_success():
    """Test verification succeeds when cookie and header tokens match."""
    token = generate_csrf_token()
    scope = {
        "type": "http",
        "headers": [
            (b"cookie", f"{CSRF_COOKIE_NAME}={token}".encode()),
            (CSRF_TOKEN_HEADER.lower().encode(), token.encode()),
        ],
    }
    request = Request(scope)
    assert validate_csrf_token(request) is True


def test_set_csrf_cookie():
    """Test that set_csrf_cookie adds the correct cookie header."""
    response = Response()
    token = "test_token"
    set_csrf_cookie(response, token)
    cookies = response.headers.getlist("set-cookie")
    assert any(f"{CSRF_COOKIE_NAME}={token}" in c for c in cookies)


def test_unset_csrf_cookie():
    """Test that unset_csrf_cookie unsets the cookie."""
    response = Response()
    unset_csrf_cookie(response)
    cookies = response.headers.getlist("set-cookie")
    assert any(f"{CSRF_COOKIE_NAME}=" in c for c in cookies)


@pytest.mark.asyncio
async def test_csrf_middleware_testing_mode(monkeypatch):
    """Test that CSRF middleware passes when in testing mode."""
    monkeypatch.setenv("TESTING", "true")
    middleware = CSRFMiddleware(DummyApp())
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/some-protected-path",
        "headers": [
            (b"authorization", b"Bearer token"),
        ]
    }
    request = Request(scope)

    async def call_next(req):
        return Response("OK")

    res = await middleware.dispatch(request, call_next)
    assert res.body == b"OK"


@pytest.mark.asyncio
async def test_csrf_middleware_dispatch_safe_method(monkeypatch):
    """Test that CSRF middleware is skipped for safe methods."""
    monkeypatch.delenv("TESTING", raising=False)
    middleware = CSRFMiddleware(DummyApp())
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/some-protected-path",
        "headers": []
    }
    request = Request(scope)

    async def call_next(req):
        return Response("OK")

    res = await middleware.dispatch(request, call_next)
    assert res.body == b"OK"


@pytest.mark.asyncio
async def test_csrf_middleware_dispatch_exempt_path(monkeypatch):
    """Test that CSRF middleware is skipped for exempt paths."""
    monkeypatch.delenv("TESTING", raising=False)
    middleware = CSRFMiddleware(DummyApp())
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/auth/login",
        "headers": []
    }
    request = Request(scope)

    async def call_next(req):
        return Response("OK")

    res = await middleware.dispatch(request, call_next)
    assert res.body == b"OK"


@pytest.mark.asyncio
async def test_csrf_middleware_dispatch_no_auth(monkeypatch):
    """Test that CSRF middleware is skipped if authorization header is absent."""
    monkeypatch.delenv("TESTING", raising=False)
    middleware = CSRFMiddleware(DummyApp())
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/some-protected-path",
        "headers": []
    }
    request = Request(scope)

    async def call_next(req):
        return Response("OK")

    res = await middleware.dispatch(request, call_next)
    assert res.body == b"OK"


@pytest.mark.asyncio
async def test_csrf_middleware_dispatch_invalid_token(monkeypatch):
    """Test that CSRF middleware rejects request if token is missing or mismatched."""
    monkeypatch.delenv("TESTING", raising=False)
    middleware = CSRFMiddleware(DummyApp())
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/some-protected-path",
        "headers": [
            (b"authorization", b"Bearer token"),
            (b"cookie", b"csrf_token=token1"),
            (CSRF_TOKEN_HEADER.lower().encode(), b"token2"),
        ]
    }
    request = Request(scope)

    async def call_next(req):
        return Response("OK")

    res = await middleware.dispatch(request, call_next)
    assert res.status_code == 403
    data = json.loads(res.body.decode())
    assert data["detail"] == "CSRF token missing or invalid"


@pytest.mark.asyncio
async def test_csrf_middleware_dispatch_valid_token(monkeypatch):
    """Test that CSRF middleware allows request with valid token."""
    monkeypatch.delenv("TESTING", raising=False)
    middleware = CSRFMiddleware(DummyApp())
    token = generate_csrf_token()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/some-protected-path",
        "headers": [
            (b"authorization", b"Bearer token"),
            (b"cookie", f"csrf_token={token}".encode()),
            (CSRF_TOKEN_HEADER.lower().encode(), token.encode()),
        ]
    }
    request = Request(scope)

    async def call_next(req):
        return Response("OK")

    res = await middleware.dispatch(request, call_next)
    assert res.body == b"OK"
