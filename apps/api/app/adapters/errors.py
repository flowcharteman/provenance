"""Standardized adapter errors; retry orchestration is owned by ingestion."""

from __future__ import annotations

from enum import Enum


class AdapterErrorStatus(str, Enum):
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    NOT_FOUND = "NOT_FOUND"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"


class AdapterError(Exception):
    def __init__(
        self,
        status: AdapterErrorStatus,
        message: str,
        *,
        retryable: bool,
        retry_after_seconds: float | None = None,
        source_system_key: str | None = None,
        http_status: int | None = None,
    ) -> None:
        if retry_after_seconds is not None and retry_after_seconds < 0:
            raise ValueError("retry_after_seconds must be non-negative")
        if retry_after_seconds is not None and not retryable:
            raise ValueError("retry_after_seconds requires a retryable error")
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.source_system_key = source_system_key
        self.http_status = http_status
