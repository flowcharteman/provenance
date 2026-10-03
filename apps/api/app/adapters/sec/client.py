"""Single-attempt HTTP client for official SEC JSON endpoints."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.adapters.errors import AdapterError, AdapterErrorStatus


_ALLOWED_HOSTS = frozenset({"www.sec.gov", "data.sec.gov"})


@dataclass(frozen=True)
class SecHttpResponse:
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes
    payload: Mapping[str, object]


class SecHttpClient:
    """Per-request transport; retries and rate limiting belong to its caller."""

    def __init__(
        self,
        user_agent: str,
        timeout_seconds: float = 20.0,
        cache_dir: str | None = None,
    ) -> None:
        if not user_agent.strip():
            raise ValueError("A configured SEC User-Agent is required")
        self._user_agent = user_agent
        self._timeout_seconds = timeout_seconds
        self._cache_dir = Path(cache_dir).expanduser() if cache_dir else None

    async def get_json(self, url: str) -> SecHttpResponse:
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.hostname not in _ALLOWED_HOSTS:
            raise ValueError("SEC adapter requests are restricted to official SEC HTTPS hosts")
        return await asyncio.to_thread(self._get_json, url)

    def _get_json(self, url: str) -> SecHttpResponse:
        cached = self._load_cache(url)
        request_headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }
        if cached is not None:
            if cached.headers.get("ETag"):
                request_headers["If-None-Match"] = cached.headers["ETag"]
            if cached.headers.get("Last-Modified"):
                request_headers["If-Modified-Since"] = cached.headers["Last-Modified"]
        request = Request(
            url,
            headers=request_headers,
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read()
                status = response.status
                headers = dict(response.headers.items())
        except HTTPError as error:
            if error.code == 304 and cached is not None:
                cached_headers = dict(cached.headers)
                if error.headers:
                    cached_headers.update(dict(error.headers.items()))
                return SecHttpResponse(
                    url=url,
                    status=304,
                    headers=cached_headers,
                    body=cached.body,
                    payload=cached.payload,
                )
            retry_after = self._retry_after(error.headers.get("Retry-After"))
            if error.code == 429:
                status_kind = AdapterErrorStatus.RATE_LIMITED
                retryable = True
            elif error.code in (408, 500, 502, 503, 504):
                status_kind = AdapterErrorStatus.TEMPORARY_FAILURE
                retryable = True
            elif error.code == 404:
                status_kind = AdapterErrorStatus.NOT_FOUND
                retryable = False
            else:
                status_kind = AdapterErrorStatus.PERMANENT_FAILURE
                retryable = False
            raise AdapterError(
                status_kind,
                f"SEC request failed with HTTP {error.code}",
                retryable=retryable,
                retry_after_seconds=retry_after if retryable else None,
                source_system_key="sec-edgar",
                http_status=error.code,
            ) from error
        except URLError as error:
            raise AdapterError(
                AdapterErrorStatus.TEMPORARY_FAILURE,
                f"SEC request transport failed: {error.reason}",
                retryable=True,
                source_system_key="sec-edgar",
            ) from error
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError(
                AdapterErrorStatus.INVALID_RESPONSE,
                "SEC returned a response that is not valid JSON",
                retryable=False,
                source_system_key="sec-edgar",
                http_status=status,
            ) from error
        if not isinstance(payload, dict):
            raise AdapterError(
                AdapterErrorStatus.INVALID_RESPONSE,
                "SEC JSON response root must be an object",
                retryable=False,
                source_system_key="sec-edgar",
                http_status=status,
            )
        response = SecHttpResponse(
            url=url,
            status=status,
            headers=headers,
            body=body,
            payload=payload,
        )
        self._save_cache(response)
        return response

    def _cache_path(self, url: str) -> Path | None:
        if self._cache_dir is None:
            return None
        name = hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json"
        return self._cache_dir / name

    def _load_cache(self, url: str) -> SecHttpResponse | None:
        path = self._cache_path(url)
        if path is None or not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as cache_file:
                cache = json.load(cache_file)
            if cache.get("url") != url:
                raise ValueError("cache URL does not match its cache key")
            body = base64.b64decode(cache["body_base64"], validate=True)
            payload = json.loads(body)
            headers = cache["headers"]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise RuntimeError(f"SEC HTTP cache entry is invalid: {path}") from error
        if not isinstance(payload, dict) or not isinstance(headers, dict):
            raise RuntimeError(f"SEC HTTP cache entry has invalid data: {path}")
        return SecHttpResponse(
            url=url,
            status=200,
            headers={str(key): str(value) for key, value in headers.items()},
            body=body,
            payload=payload,
        )

    def _save_cache(self, response: SecHttpResponse) -> None:
        path = self._cache_path(response.url)
        if path is None:
            return
        cache_headers = {
            key: response.headers[key]
            for key in ("ETag", "Last-Modified")
            if key in response.headers
        }
        if not cache_headers:
            return
        cache_value = {
            "url": response.url,
            "headers": cache_headers,
            "body_base64": base64.b64encode(response.body).decode("ascii"),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".sec-cache-",
            dir=str(path.parent),
            text=True,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as cache_file:
                json.dump(cache_value, cache_file, separators=(",", ":"))
                cache_file.flush()
                os.fsync(cache_file.fileno())
            os.replace(temporary_path, path)
        except OSError:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _retry_after(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
            except (TypeError, ValueError, OverflowError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
