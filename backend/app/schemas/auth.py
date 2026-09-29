# =============================================================================
# backend/app/schemas/auth.py
#
# Pydantic request/response models for the /api/auth endpoints.
# =============================================================================

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class CurrentUser(BaseModel):
    """The logged-in employee (never contains any credential)."""

    id: int
    username: str
    display_name: str
    is_admin: bool
    must_change_password: bool


class TemporaryPassword(BaseModel):
    """Shown once to the administrator after a reset."""

    employee_id: int
    username: str
    temporary_password: str


class AuthConfig(BaseModel):
    """Public information the clients need before login."""

    auth_enabled: bool
