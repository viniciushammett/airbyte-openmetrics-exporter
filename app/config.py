from __future__ import annotations

import logging
import re
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_METRIC_PREFIX_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    airbyte_db_host: str = Field(alias="AIRBYTE_DB_HOST", min_length=1)
    airbyte_db_port: Annotated[int, Field(ge=1, le=65535)] = Field(default=5432, alias="AIRBYTE_DB_PORT")
    airbyte_db_name: str = Field(alias="AIRBYTE_DB_NAME", min_length=1)
    airbyte_db_user: str = Field(alias="AIRBYTE_DB_USER", min_length=1)
    airbyte_db_password: SecretStr = Field(alias="AIRBYTE_DB_PASSWORD")
    airbyte_db_sslmode: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"] = Field(
        default="prefer",
        alias="AIRBYTE_DB_SSLMODE",
    )

    exporter_host: str = Field(default="0.0.0.0", alias="EXPORTER_HOST", min_length=1)
    exporter_port: Annotated[int, Field(ge=1, le=65535)] = Field(default=8000, alias="EXPORTER_PORT")
    metrics_prefix: str = Field(default="airbyte", alias="METRICS_PREFIX")

    query_timeout_seconds: Annotated[int, Field(ge=1, le=300)] = Field(default=10, alias="QUERY_TIMEOUT_SECONDS")
    scrape_cache_ttl_seconds: Annotated[int, Field(ge=0, le=3600)] = Field(default=30, alias="SCRAPE_CACHE_TTL_SECONDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("metrics_prefix")
    @classmethod
    def validate_metrics_prefix(cls, value: str) -> str:
        normalized = value.strip().lower().replace("-", "_").strip("_") or "airbyte"
        if not _METRIC_PREFIX_RE.match(normalized):
            raise ValueError("METRICS_PREFIX must normalize to a valid Prometheus metric prefix")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR or CRITICAL")
        return normalized

    def db_connect_kwargs(self) -> dict[str, object]:
        """Return psycopg2 connection kwargs without building a password-bearing DSN string."""
        return {
            "host": self.airbyte_db_host,
            "port": self.airbyte_db_port,
            "dbname": self.airbyte_db_name,
            "user": self.airbyte_db_user,
            "password": self.airbyte_db_password.get_secret_value(),
            "connect_timeout": self.query_timeout_seconds,
            "sslmode": self.airbyte_db_sslmode,
            "application_name": "airbyte-openmetrics-exporter",
        }

    def safe_db_label(self) -> str:
        return f"{self.airbyte_db_host}:{self.airbyte_db_port}/{self.airbyte_db_name}"

    @property
    def normalized_metrics_prefix(self) -> str:
        return self.metrics_prefix


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
