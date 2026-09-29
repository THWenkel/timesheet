# =============================================================================
# backend/app/core/security.py
#
# Authentication: password hashing, JWT session cookie, CSRF check, and the
# FastAPI dependencies that protect the routers.
#
# How it works
#   * POST /api/auth/login verifies username + password (Argon2id) and sets two
#     cookies: the JWT in an HttpOnly cookie (JavaScript cannot read it) and a
#     CSRF token in a readable cookie. The same CSRF value is a claim inside
#     the JWT.
#   * Every state-changing request (POST/PUT/PATCH/DELETE) must send the CSRF
#     value in the X-CSRF-Token header. It is compared with the JWT claim, so a
#     foreign site that can trigger requests but cannot read the cookie fails.
#   * Tokens carry the time of the last password change ("pwd"). Changing or
#     resetting a password invalidates all tokens issued before.
#   * With AUTH_ENABLED=false the dependencies below let everything through,
#     as before. Enable it in production together with a strong SECRET_KEY.
#
# HTTPS: TLS terminates at the reverse proxy (see INSTALL_IIS_INTRANET.md).
# COOKIE_SECURE=true (default) makes browsers send the cookies over HTTPS only.
# =============================================================================

import hmac
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.employee import Employee

ALGORITHM = "HS256"
CSRF_HEADER = "X-CSRF-Token"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

_hasher = PasswordHasher()
# Verified against when the user does not exist, so timing does not reveal usernames.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


@dataclass(frozen=True)
class AuthContext:
    """The authenticated caller of a request."""

    employee_id: int
    is_admin: bool


def utcnow() -> datetime:
    """Naive UTC 'now' without microseconds (the DATETIME columns hold naive UTC)."""
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


# -----------------------------------------------------------------------------
# Passwords
# -----------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Check a password. Always does the hashing work, even for unknown users."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except VerificationError, InvalidHashError:
        return False


def password_policy_error(password: str) -> str | None:
    """Return a message if the password is not acceptable, else None."""
    if len(password) < settings.password_min_length:
        return f"Password must be at least {settings.password_min_length} characters long"
    if len(password) > 128:
        return "Password must not be longer than 128 characters"
    if password.strip() != password:
        return "Password must not start or end with whitespace"
    return None


# -----------------------------------------------------------------------------
# Token and cookies
# -----------------------------------------------------------------------------
def _password_stamp(employee: Employee) -> int:
    changed = employee.password_changed_at
    return int(changed.replace(tzinfo=UTC).timestamp()) if changed else 0


def issue_session(response: Response, employee: Employee) -> None:
    """Create a JWT for the employee and set the session and CSRF cookies."""
    csrf = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    token = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
        {
            "sub": str(employee.id),
            "iat": now,
            "exp": now + lifetime,
            "csrf": csrf,
            "pwd": _password_stamp(employee),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    max_age = int(lifetime.total_seconds())
    common: dict[str, Any] = {
        "max_age": max_age,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(settings.cookie_name, token, httponly=True, **common)
    # Readable by the frontend so it can echo the value in the X-CSRF-Token header.
    response.set_cookie(settings.csrf_cookie_name, csrf, httponly=False, **common)


def clear_session(response: Response) -> None:
    for name in (settings.cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(name, path="/", secure=settings.cookie_secure, samesite="lax")


def _decode(token: str) -> dict[str, Any] | None:
    try:
        payload: dict[str, Any] = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub", "csrf", "pwd"]},
        )
    except jwt.PyJWTError:
        return None
    return payload


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


def _authenticate(
    request: Request, db: Session, *, allow_password_change: bool, force: bool
) -> AuthContext | None:
    """Validate the session cookie. Returns None only when auth is disabled."""
    if not settings.auth_enabled and not force:
        return None
    token = request.cookies.get(settings.cookie_name)
    payload = _decode(token) if token else None
    if payload is None:
        raise _unauthorized()
    try:
        employee = db.get(Employee, int(payload["sub"]))
    except ValueError, TypeError:
        raise _unauthorized() from None
    if employee is None or not employee.is_active or payload["pwd"] != _password_stamp(employee):
        raise _unauthorized()

    if request.method not in _SAFE_METHODS:
        sent = request.headers.get(CSRF_HEADER, "")
        if not hmac.compare_digest(sent.encode(), str(payload["csrf"]).encode()):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF token missing or invalid")

    if employee.must_change_password and not allow_password_change:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Password change required")
    return AuthContext(employee_id=employee.id, is_admin=employee.is_admin)


# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------
def require_user(request: Request, db: Session = Depends(get_db)) -> AuthContext | None:
    """Any logged-in employee. No-op while AUTH_ENABLED=false."""
    return _authenticate(request, db, allow_password_change=False, force=False)


def require_login(request: Request, db: Session = Depends(get_db)) -> AuthContext:
    """A logged-in employee, even if they still must change their password."""
    context = _authenticate(request, db, allow_password_change=True, force=True)
    if context is None:  # pragma: no cover - force=True never returns None
        raise _unauthorized()
    return context


def require_admin(auth: AuthContext | None = Depends(require_user)) -> AuthContext | None:
    """An administrator. No-op while AUTH_ENABLED=false."""
    if auth is not None and not auth.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator rights required")
    return auth


def ensure_employee_access(auth: AuthContext | None, employee_id: int) -> None:
    """Non-admins may only touch their own data."""
    if auth is not None and not auth.is_admin and auth.employee_id != employee_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access to another employee's data denied")


# -----------------------------------------------------------------------------
# Response headers
# -----------------------------------------------------------------------------
async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add browser hardening headers. HSTS only when cookies are HTTPS-only."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Cache-Control", "no-store")
    if settings.cookie_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response
