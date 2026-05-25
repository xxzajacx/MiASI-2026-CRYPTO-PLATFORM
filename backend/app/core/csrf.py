"""CSRF protection middleware and utilities."""
import hashlib
import secrets
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


CSRF_TOKEN_HEADER = "X-CSRF-TOKEN"
CSRF_COOKIE_NAME = "csrf_token"


def generate_csrf_token() -> str:
    """Generate a new CSRF token."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(request: Request) -> bool:
    """Validate CSRF token from request header against cookie."""
    # Get token from cookie
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token:
        return False
    
    # Get token from header
    header_token = request.headers.get(CSRF_TOKEN_HEADER)
    if not header_token:
        return False
    
    # Compare tokens (use constant-time comparison)
    return secrets.compare_digest(cookie_token, header_token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to validate CSRF tokens for state-changing operations."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Methods that require CSRF protection
        self.protected_methods = {"POST", "PUT", "DELETE", "PATCH"}
        # Paths that are exempt from CSRF protection
        self.exempt_paths = {
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/verify-2fa",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
    
    async def dispatch(self, request: Request, call_next):
        import os
        if os.getenv("TESTING") == "true":
            return await call_next(request)
        # Skip CSRF for safe methods
        if request.method not in self.protected_methods:
            return await call_next(request)
        
        # Skip CSRF for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Skip CSRF for requests without auth (they'll fail auth anyway)
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return await call_next(request)
        
        # Validate CSRF token
        if not validate_csrf_token(request):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing or invalid"}
            )
        
        return await call_next(request)


def set_csrf_cookie(response: Response, token: str) -> None:
    """Set CSRF token in cookie."""
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Must be False so JavaScript can read it
        samesite="lax",  # Changed from strict to lax to be more forgiving during dev
        secure=False,  # Set to True in production with HTTPS
        path="/"
    )


def unset_csrf_cookie(response: Response) -> None:
    """Remove CSRF cookie on logout."""
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")
