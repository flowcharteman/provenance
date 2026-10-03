"""Configuration without embedded credentials or provider identities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import quote


@dataclass(frozen=True)
class Settings:
    database_url: str
    sec_user_agent_name: str
    sec_contact_email: str
    sec_requests_per_second: float = 8.0
    sec_max_retries: int = 4
    sec_initial_backoff_seconds: float = 1.0
    sec_max_backoff_seconds: float = 30.0
    sec_request_timeout_seconds: float = 20.0
    sec_http_cache_dir: str = str(
        Path.home() / ".cache" / "investment-analysis" / "sec-edgar"
    )

    @property
    def sec_user_agent(self) -> str:
        if not self.sec_user_agent_name.strip():
            raise ValueError("SEC_USER_AGENT_NAME must be configured")
        parsed_email = parseaddr(self.sec_contact_email)[1]
        if not parsed_email or "@" not in parsed_email:
            raise ValueError("SEC_CONTACT_EMAIL must be a valid contact email")
        return f"{self.sec_user_agent_name.strip()} {parsed_email}"

    @classmethod
    def from_env(cls) -> "Settings":
        cache_dir = os.environ.get("SEC_HTTP_CACHE_DIR", "").strip()
        database_url = os.environ.get("DATABASE_URL", "").strip()
        if not database_url:
            password = os.environ.get("POSTGRES_PASSWORD", "")
            if not password:
                raise ValueError(
                    "Set DATABASE_URL or configure POSTGRES_PASSWORD for the local database"
                )
            user = os.environ.get("POSTGRES_USER", "investment_app")
            database = os.environ.get("POSTGRES_DB", "investment_analysis")
            host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
            port = os.environ.get("POSTGRES_PORT", "5432")
            database_url = (
                f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}"
                f"@{host}:{port}/{quote(database, safe='')}"
            )
        settings = cls(
            database_url=database_url,
            sec_user_agent_name=os.environ.get("SEC_USER_AGENT_NAME", "").strip(),
            sec_contact_email=os.environ.get("SEC_CONTACT_EMAIL", "").strip(),
            sec_requests_per_second=float(
                os.environ.get("SEC_REQUESTS_PER_SECOND", "8")
            ),
            sec_max_retries=int(os.environ.get("SEC_MAX_RETRIES", "4")),
            sec_initial_backoff_seconds=float(
                os.environ.get("SEC_INITIAL_BACKOFF_SECONDS", "1")
            ),
            sec_max_backoff_seconds=float(
                os.environ.get("SEC_MAX_BACKOFF_SECONDS", "30")
            ),
            sec_request_timeout_seconds=float(
                os.environ.get("SEC_REQUEST_TIMEOUT_SECONDS", "20")
            ),
            sec_http_cache_dir=os.path.expanduser(
                cache_dir
                or str(Path.home() / ".cache" / "investment-analysis" / "sec-edgar")
            ),
        )
        if settings.sec_requests_per_second <= 0 or settings.sec_requests_per_second > 10:
            raise ValueError("SEC_REQUESTS_PER_SECOND must be greater than 0 and at most 10")
        if settings.sec_max_retries < 0:
            raise ValueError("SEC_MAX_RETRIES must be non-negative")
        if settings.sec_initial_backoff_seconds <= 0:
            raise ValueError("SEC_INITIAL_BACKOFF_SECONDS must be greater than 0")
        if settings.sec_max_backoff_seconds < settings.sec_initial_backoff_seconds:
            raise ValueError(
                "SEC_MAX_BACKOFF_SECONDS must be at least SEC_INITIAL_BACKOFF_SECONDS"
            )
        if settings.sec_request_timeout_seconds <= 0:
            raise ValueError("SEC_REQUEST_TIMEOUT_SECONDS must be greater than 0")
        return settings
