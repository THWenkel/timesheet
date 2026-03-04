# =============================================================================
# backend/app/core/config.py
#
# Application configuration via pydantic-settings.
# Values are read from environment variables or a .env file.
#
# ⚠️  SECURITY TODO (before go-live):
#   - Replace DB_USER / DB_PASSWORD with a dedicated least-privilege SQL account.
#   - Store secrets in a proper secrets manager (Azure Key Vault, HashiCorp Vault).
#   - Enable encrypted connection: set DB_ENCRYPT=yes and provide a valid TLS cert.
# =============================================================================

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings.

    All fields can be overridden via environment variables or a .env file
    located in the backend/ directory.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # -------------------------------------------------------------------------
    # Database connection — Microsoft SQL Server 2012
    # -------------------------------------------------------------------------
    db_server: str = Field(default="dbserver01", description="SQL Server hostname")
    db_name: str = Field(default="WiTERP", description="SQL Server database name")
    db_user: str = Field(default="sa", description="SQL Server login username")
    db_password: str = Field(
        ...,  # required — no default, must be supplied via env / .env
        description="SQL Server login password",
    )
    # Encrypt=no is required for SQL Server 2012 without a valid TLS certificate.
    # ⚠️  TODO: Set to 'yes' and configure TLS before going to production.
    db_encrypt: str = Field(default="no", description="ODBC Encrypt setting")

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_title: str = Field(default="Timesheet API")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)

    # -------------------------------------------------------------------------
    # Authentication placeholder
    # ⚠️  TODO: Enable and configure before production.
    # -------------------------------------------------------------------------
    auth_enabled: bool = Field(
        default=False,
        description="Set to True to enforce JWT authentication (v2+)",
    )
    secret_key: str = Field(
        default="change-me-before-production",
        description="JWT signing secret — MUST be changed before go-live",
    )
    access_token_expire_minutes: int = Field(default=60)


# Module-level settings instance — import this everywhere
settings = Settings()  # type: ignore[call-arg]
