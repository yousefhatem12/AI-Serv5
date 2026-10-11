from __future__ import annotations
import hmac
import threading
import time
from typing import Optional

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import get_app_settings
from src.core.security import get_client_ip, http_bearer, api_key_header, verify_api_key


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter per client identifier (IP / API key).
    Provides abuse and flood protection for CV extraction endpoints.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._clients: dict[str, list[float]] = {}
        self._last_cleanup = time.time()

    def is_allowed(self, client_id: str, limit_per_minute: int) -> tuple[bool, int]:
        """
        Checks if client request is within rate limit.
        Returns (is_allowed, retry_after_seconds).
        """
        if limit_per_minute <= 0:
            return True, 0

        now = time.time()
        window_start = now - 60.0

        with self._lock:
            # Periodic cleanup of inactive clients every 5 minutes
            if now - self._last_cleanup > 300:
                self._cleanup_stale(window_start)
                self._last_cleanup = now

            timestamps = self._clients.setdefault(client_id, [])
            # Filter timestamps within current 60s sliding window
            self._clients[client_id] = [t for t in timestamps if t > window_start]
            current_count = len(self._clients[client_id])

            if current_count >= limit_per_minute:
                oldest_timestamp = self._clients[client_id][0]
                retry_after = max(1, int(60.0 - (now - oldest_timestamp)))
                return False, retry_after

            self._clients[client_id].append(now)
            return True, 0

    def _cleanup_stale(self, window_start: float) -> None:
        stale_keys = [k for k, v in self._clients.items() if not v or v[-1] <= window_start]
        for k in stale_keys:
            del self._clients[k]

    def reset(self) -> None:
        """Clears all rate limit records (primarily for testing)."""
        with self._lock:
            self._clients.clear()


# Global rate limiter instance
rate_limiter = SlidingWindowRateLimiter()


# Canonical safe rate-limit client identity resolver from src.core.security
get_client_identifier = get_client_ip


# verify_api_key is canonically defined in src.core.security and imported above.


async def require_service_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
    api_key_header_val: str | None = Security(api_key_header),
) -> str:
    """Require the already-configured service key for internal write operations.

    This service has no authenticated candidate principal yet.  Routes using
    this dependency are therefore server-to-server integration points: the
    caller (for example, Laravel) must authenticate and authorize the
    candidate before forwarding the event.  Unlike ``verify_api_key``, this is
    never disabled by the public-read API-key feature flag.
    """
    app_settings = get_app_settings()
    configured_key = getattr(app_settings, "api_key", None)
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "detail": "Interaction event ingestion is unavailable until SERVICE_API_KEY is configured.",
                "error_code": "SERVICE_AUTH_NOT_CONFIGURED",
            },
        )

    provided_key: Optional[str] = None
    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        provided_key = credentials.credentials.strip()
    elif api_key_header_val:
        provided_key = api_key_header_val.strip()
    else:
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            provided_key = auth_header[7:].strip()
        elif request.headers.get("x-api-key"):
            provided_key = request.headers.get("x-api-key", "").strip()

    if not provided_key or not hmac.compare_digest(provided_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid or missing service API key.", "error_code": "UNAUTHORIZED"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return provided_key


async def check_rate_limit(request: Request) -> None:
    """
    Dependency that enforces rate limits on incoming API calls.
    """
    app_settings = get_app_settings()
    if not app_settings.enable_rate_limiting:
        return

    client_id = get_client_identifier(request)
    allowed, retry_after = rate_limiter.is_allowed(
        client_id=client_id,
        limit_per_minute=app_settings.rate_limit_per_minute
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"detail": f"Rate limit exceeded. Try again in {retry_after} seconds.", "error_code": "RATE_LIMIT_EXCEEDED"},
            headers={"Retry-After": str(retry_after)}
        )
