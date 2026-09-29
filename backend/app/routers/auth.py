# =============================================================================
# backend/app/routers/auth.py
#
# FastAPI router for the /api/auth endpoints.
#
# Endpoints:
#   GET  /api/auth/config                      — is authentication enforced?
#   POST /api/auth/login                       — username + password -> session cookies
#   POST /api/auth/logout                      — clear the session cookies
#   GET  /api/auth/me                          — the logged-in user
#   POST /api/auth/change-password             — change own password
#   POST /api/auth/admin/reset-password/{id}   — admin: set a one-time password
# =============================================================================

import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    AuthContext,
    clear_session,
    hash_password,
    issue_session,
    password_policy_error,
    require_admin,
    require_login,
    utcnow,
    verify_password,
)
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.auth import (
    AuthConfig,
    ChangePasswordRequest,
    CurrentUser,
    LoginRequest,
    TemporaryPassword,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# One message for every failure, so it does not reveal which usernames exist.
_INVALID_LOGIN = "Invalid username or password, or account temporarily locked"


def _to_user(employee: Employee) -> CurrentUser:
    return CurrentUser(
        id=employee.id,
        username=employee.username or "",
        display_name=employee.display_name,
        is_admin=employee.is_admin,
        must_change_password=employee.must_change_password,
    )


@router.get("/config", response_model=AuthConfig, summary="Is authentication enforced?")
def auth_config() -> AuthConfig:
    """Public. Lets the admin client skip the login while AUTH_ENABLED=false (first setup)."""
    return AuthConfig(auth_enabled=settings.auth_enabled)


@router.post("/login", response_model=CurrentUser, summary="Log in")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> CurrentUser:
    username = payload.username.strip().lower()
    employee = db.execute(
        select(Employee).where(Employee.username == username)
    ).scalar_one_or_none()

    now = utcnow()
    locked = (
        employee is not None and employee.locked_until is not None and employee.locked_until > now
    )
    # Always run the password check (constant work), then decide.
    password_ok = verify_password(employee.password_hash if employee else None, payload.password)

    if employee is None or not employee.is_active or locked or not password_ok:
        if employee is not None and employee.is_active and not locked:
            employee.failed_login_count += 1
            if employee.failed_login_count >= settings.max_failed_logins:
                employee.locked_until = now + timedelta(minutes=settings.lockout_minutes)
                employee.failed_login_count = 0
                logger.warning("Account '%s' locked after repeated failed logins", username)
            db.commit()
        logger.info("Failed login for '%s'", username)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _INVALID_LOGIN)

    employee.failed_login_count = 0
    employee.locked_until = None
    db.commit()
    issue_session(response, employee)
    return _to_user(employee)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log out")
def logout(response: Response) -> None:
    clear_session(response)


@router.get("/me", response_model=CurrentUser, summary="The logged-in user")
def me(auth: AuthContext = Depends(require_login), db: Session = Depends(get_db)) -> CurrentUser:
    employee = db.get(Employee, auth.employee_id)
    if employee is None:  # pragma: no cover - already checked by require_login
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return _to_user(employee)


@router.post("/change-password", response_model=CurrentUser, summary="Change own password")
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    auth: AuthContext = Depends(require_login),
    db: Session = Depends(get_db),
) -> CurrentUser:
    employee = db.get(Employee, auth.employee_id)
    if employee is None:  # pragma: no cover - already checked by require_login
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if not verify_password(employee.password_hash, payload.current_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "New password must differ from the old one"
        )
    problem = password_policy_error(payload.new_password)
    if problem:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, problem)

    employee.password_hash = hash_password(payload.new_password)
    employee.must_change_password = False
    employee.password_changed_at = utcnow()
    db.commit()
    # All older tokens are now invalid; continue this session with a fresh one.
    issue_session(response, employee)
    return _to_user(employee)


@router.post(
    "/admin/reset-password/{employee_id}",
    response_model=TemporaryPassword,
    summary="Admin: set a one-time password (user must change it at next login)",
)
def reset_password(
    employee_id: int,
    db: Session = Depends(get_db),
    _admin: AuthContext | None = Depends(require_admin),
) -> TemporaryPassword:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Employee with id={employee_id} not found")
    if not employee.username:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Set a username for the employee first")

    temporary = secrets.token_urlsafe(12)
    employee.password_hash = hash_password(temporary)
    employee.must_change_password = True
    employee.password_changed_at = utcnow()
    employee.failed_login_count = 0
    employee.locked_until = None
    db.commit()
    logger.info("Temporary password set for employee %s", employee_id)
    return TemporaryPassword(
        employee_id=employee.id, username=employee.username, temporary_password=temporary
    )
