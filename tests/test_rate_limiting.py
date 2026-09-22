import hashlib
import time
import pytest
from unittest.mock import patch, MagicMock
from starlette.requests import Request
from fastapi.testclient import TestClient
from src.main import app
from src.core.config import settings
from src.core.security import rate_limiter, InMemoryRateLimiter, RedisRateLimiter, get_client_ip

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_limiter_state():
    """Ensure a clean rate limiter state before and after each test."""
    rate_limiter.reset()
    original_enabled = settings.RATE_LIMIT_ENABLED
    original_requests = settings.RATE_LIMIT_REQUESTS
    original_window = settings.RATE_LIMIT_WINDOW_SECONDS
    yield
    rate_limiter.reset()
    settings.RATE_LIMIT_ENABLED = original_enabled
    settings.RATE_LIMIT_REQUESTS = original_requests
    settings.RATE_LIMIT_WINDOW_SECONDS = original_window

def test_rate_limiting_headers_on_api_endpoints():
    """Verify standard RFC RateLimit headers are attached to API responses."""
    settings.RATE_LIMIT_ENABLED = True
    settings.RATE_LIMIT_REQUESTS = 10
    settings.RATE_LIMIT_WINDOW_SECONDS = 60

    headers = {"X-Forwarded-For": "203.0.113.195"}
    response = client.get("/api/v1/review-queue/", headers=headers)
    assert response.status_code == 200

    assert "X-RateLimit-Limit" in response.headers
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert "X-RateLimit-Remaining" in response.headers
    assert response.headers["X-RateLimit-Remaining"] == "9"
    assert "X-RateLimit-Reset" in response.headers
    assert response.headers["X-RateLimit-Reset"] == "60"

def test_rate_limiting_decrements_quota():
    """Verify remaining count decrements with each consecutive request."""
    settings.RATE_LIMIT_ENABLED = True
    settings.RATE_LIMIT_REQUESTS = 5
    settings.RATE_LIMIT_WINDOW_SECONDS = 60

    headers = {"X-Forwarded-For": "198.51.100.1"}

    for i in range(4):
        resp = client.get("/api/v1/review-queue/", headers=headers)
        assert resp.status_code == 200
        expected_remaining = str(5 - (i + 1))
        assert resp.headers["X-RateLimit-Remaining"] == expected_remaining

def test_rate_limiting_enforcement_returns_429():
    """Verify that exceeding the quota returns HTTP 429 with standard headers and error body."""
    settings.RATE_LIMIT_ENABLED = True
    settings.RATE_LIMIT_REQUESTS = 3
    settings.RATE_LIMIT_WINDOW_SECONDS = 30

    headers = {"X-Forwarded-For": "198.51.100.42"}

    # Consume available quota (3 requests)
    for _ in range(3):
        res = client.get("/api/v1/review-queue/", headers=headers)
        assert res.status_code == 200

    # 4th request must be throttled with HTTP 429
    blocked = client.get("/api/v1/review-queue/", headers=headers)
    assert blocked.status_code == 429

    assert "Retry-After" in blocked.headers
    assert int(blocked.headers["Retry-After"]) > 0
    assert blocked.headers["X-RateLimit-Remaining"] == "0"
    assert blocked.headers["X-RateLimit-Limit"] == "3"

    body = blocked.json()
    assert body["error"] == "RATE_LIMIT_EXCEEDED"
    assert "retry_after" in body
    assert body["retry_after"] > 0

def test_rate_limiting_exempt_paths():
    """Verify health check and documentation endpoints are exempt from rate limiting."""
    settings.RATE_LIMIT_ENABLED = True
    settings.RATE_LIMIT_REQUESTS = 2
    settings.RATE_LIMIT_WINDOW_SECONDS = 60

    headers = {"X-Forwarded-For": "192.0.2.1"}

    # Hit health endpoint many times beyond the limit
    for _ in range(10):
        resp = client.get("/health", headers=headers)
        assert resp.status_code == 200

    # Hit root endpoint beyond the limit
    for _ in range(10):
        resp = client.get("/", headers=headers)
        assert resp.status_code == 200

def test_rate_limiting_client_isolation():
    """Verify distinct clients (via X-Client-ID) maintain independent quotas."""
    settings.RATE_LIMIT_ENABLED = True
    settings.RATE_LIMIT_REQUESTS = 2
    settings.RATE_LIMIT_WINDOW_SECONDS = 60

    client_a_headers = {"X-Client-ID": "client-alpha"}
    client_b_headers = {"X-Client-ID": "client-beta"}

    # Client A consumes quota
    res1 = client.get("/api/v1/review-queue/", headers=client_a_headers)
    assert res1.status_code == 200
    res2 = client.get("/api/v1/review-queue/", headers=client_a_headers)
    assert res2.status_code == 200
    res3 = client.get("/api/v1/review-queue/", headers=client_a_headers)
    assert res3.status_code == 429

    # Client B should still have full quota
    res_b = client.get("/api/v1/review-queue/", headers=client_b_headers)
    assert res_b.status_code == 200
    assert res_b.headers["X-RateLimit-Remaining"] == "1"

def test_rate_limiting_disabled_toggle():
    """Verify requests bypass throttling when RATE_LIMIT_ENABLED is False."""
    settings.RATE_LIMIT_ENABLED = False
    settings.RATE_LIMIT_REQUESTS = 2
    settings.RATE_LIMIT_WINDOW_SECONDS = 60

    headers = {"X-Forwarded-For": "172.16.0.100"}

    for _ in range(6):
        resp = client.get("/api/v1/review-queue/", headers=headers)
        assert resp.status_code == 200
        # Headers should not be attached when disabled
        assert "X-RateLimit-Limit" not in resp.headers

def test_in_memory_rate_limiter_unit_logic():
    """Unit test for InMemoryRateLimiter sliding window tracking and expiration."""
    limiter = InMemoryRateLimiter()

    # Allow 2 requests per 1-second window
    allowed, remaining, _ = limiter.check("test-client", max_requests=2, window_seconds=1)
    assert allowed is True
    assert remaining == 1

    allowed, remaining, _ = limiter.check("test-client", max_requests=2, window_seconds=1)
    assert allowed is True
    assert remaining == 0

    # 3rd request should fail
    allowed, remaining, retry_after = limiter.check("test-client", max_requests=2, window_seconds=1)
    assert allowed is False
    assert remaining == 0
    assert retry_after >= 1

    # Reset clears quota
    limiter.reset("test-client")
    allowed, remaining, _ = limiter.check("test-client", max_requests=2, window_seconds=1)
    assert allowed is True
    assert remaining == 1


# ── Focused Security & Identity Tests ─────────────────────────────────────────

def test_api_key_hashing_in_derived_identifier():
    """Verify raw API key is hashed with SHA-256 and never appears plaintext."""
    raw_key = "sk-super-secret-key-12345"
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-api-key", raw_key.encode("utf-8"))],
        "client": ("127.0.0.1", 12345),
    }
    req = Request(scope)
    derived = get_client_ip(req)

    # 1. Raw key is NOT present in derived identifier
    assert raw_key not in derived

    # 2. Key is deterministic SHA-256
    expected_digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    assert derived == f"key:{expected_digest}"

    # 3. Same key produces same identifier
    assert get_client_ip(Request(scope)) == derived

    # 4. Different key produces different identifier
    diff_scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-api-key", b"different-secret-key-67890")],
        "client": ("127.0.0.1", 12345),
    }
    assert get_client_ip(Request(diff_scope)) != derived


def test_identity_precedence_api_key_over_client_id():
    """Verify X-API-Key takes strict precedence over X-Client-ID."""
    raw_key = "sk-secret-precedence-test"
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (b"x-api-key", raw_key.encode("utf-8")),
            (b"x-client-id", b"client-bypass-attempt-1"),
        ],
        "client": ("127.0.0.1", 12345),
    }
    req1 = Request(scope)
    derived1 = get_client_ip(req1)
    expected_digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    assert derived1 == f"key:{expected_digest}"
    assert "client-bypass-attempt-1" not in derived1

    # Changing X-Client-ID while keeping X-API-Key produces identical identifier
    scope2 = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (b"x-api-key", raw_key.encode("utf-8")),
            (b"x-client-id", b"client-bypass-attempt-2"),
        ],
        "client": ("127.0.0.1", 12345),
    }
    req2 = Request(scope2)
    assert get_client_ip(req2) == derived1


def test_changing_client_id_does_not_bypass_api_key_quota():
    """Verify rotating X-Client-ID cannot bypass an API key's rate limit quota."""
    settings.RATE_LIMIT_ENABLED = True
    settings.RATE_LIMIT_REQUESTS = 2
    settings.RATE_LIMIT_WINDOW_SECONDS = 60

    api_key = "fixed-test-api-key"
    res1 = client.get("/api/v1/review-queue/", headers={"X-API-Key": api_key, "X-Client-ID": "id-1"})
    assert res1.status_code == 200

    res2 = client.get("/api/v1/review-queue/", headers={"X-API-Key": api_key, "X-Client-ID": "id-2"})
    assert res2.status_code == 200

    # 3rd request with different X-Client-ID must be throttled by API key bucket
    res3 = client.get("/api/v1/review-queue/", headers={"X-API-Key": api_key, "X-Client-ID": "id-3"})
    assert res3.status_code == 429


def test_x_client_id_when_no_api_key():
    """Verify X-Client-ID is used when no API key is supplied."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-client-id", b"mobile-app-client")],
        "client": ("127.0.0.1", 12345),
    }
    req = Request(scope)
    assert get_client_ip(req) == "client:mobile-app-client"


def test_direct_ip_when_no_key_or_client_id():
    """Verify request.client.host is used when neither API key nor client ID exists."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "client": ("192.168.1.50", 12345),
    }
    req = Request(scope)
    assert get_client_ip(req) == "192.168.1.50"


def test_spoofed_proxy_headers_cannot_bypass_rate_limit():
    """Verify spoofing X-Forwarded-For or X-Real-IP does not bypass rate limits."""
    settings.RATE_LIMIT_ENABLED = True
    settings.RATE_LIMIT_REQUESTS = 2
    settings.RATE_LIMIT_WINDOW_SECONDS = 60

    r1 = client.get("/api/v1/review-queue/", headers={"X-Forwarded-For": "1.1.1.1"})
    assert r1.status_code == 200

    r2 = client.get("/api/v1/review-queue/", headers={"X-Forwarded-For": "2.2.2.2"})
    assert r2.status_code == 200

    # 3rd request with different spoofed IP must hit 429 because it comes from same peer
    r3 = client.get("/api/v1/review-queue/", headers={"X-Forwarded-For": "3.3.3.3", "X-Real-IP": "4.4.4.4"})
    assert r3.status_code == 429


def test_raw_api_key_never_stored_in_limiter_or_redis():
    """Verify raw API key is never stored in limiter memory."""
    raw_key = "super-secret-production-token-999"
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-api-key", raw_key.encode("utf-8"))],
        "client": ("127.0.0.1", 12345),
    }
    req = Request(scope)
    derived = get_client_ip(req)
    assert raw_key not in derived

    limiter = InMemoryRateLimiter()
    limiter.check(derived, max_requests=5, window_seconds=60)
    assert raw_key not in limiter._records
    assert derived in limiter._records


def test_redis_rate_limiter_reset_specific_key():
    """Verify reset(key=...) deletes exactly one derived Redis key without scanning."""
    limiter = RedisRateLimiter(key_prefix="ratelimit:test:")
    mock_client = MagicMock()

    with patch("src.core.security.get_redis_client", return_value=mock_client):
        limiter.reset(key="client_alpha")
        mock_client.delete.assert_called_once_with("ratelimit:test:client_alpha")
        mock_client.scan_iter.assert_not_called()
        mock_client.keys.assert_not_called()


def test_redis_rate_limiter_reset_all_uses_scan_iter_and_never_keys():
    """Verify reset(None) uses non-blocking scan_iter and never calls blocking keys()."""
    limiter = RedisRateLimiter(key_prefix="ratelimit:test:")
    mock_client = MagicMock()
    mock_client.scan_iter.return_value = iter(["ratelimit:test:k1", "ratelimit:test:k2"])

    with patch("src.core.security.get_redis_client", return_value=mock_client):
        limiter.reset(key=None)
        mock_client.keys.assert_not_called()
        mock_client.scan_iter.assert_called_once_with(match="ratelimit:test:*", count=100)
        mock_client.delete.assert_called_once_with("ratelimit:test:k1", "ratelimit:test:k2")


def test_redis_rate_limiter_reset_all_batched_multi_batch_and_partial():
    """Verify reset(None) deletes in batches of 100 and deletes any final partial batch."""
    limiter = RedisRateLimiter(key_prefix="ratelimit:test:")
    keys_250 = [f"ratelimit:test:k_{i}" for i in range(250)]
    mock_client = MagicMock()
    mock_client.scan_iter.return_value = iter(keys_250)

    with patch("src.core.security.get_redis_client", return_value=mock_client):
        limiter.reset(key=None)

        assert mock_client.delete.call_count == 3
        # First batch: 100 keys
        call1_args = mock_client.delete.call_args_list[0][0]
        assert len(call1_args) == 100
        assert call1_args == tuple(keys_250[:100])

        # Second batch: 100 keys
        call2_args = mock_client.delete.call_args_list[1][0]
        assert len(call2_args) == 100
        assert call2_args == tuple(keys_250[100:200])

        # Third batch: final partial 50 keys
        call3_args = mock_client.delete.call_args_list[2][0]
        assert len(call3_args) == 50
        assert call3_args == tuple(keys_250[200:250])


def test_redis_rate_limiter_reset_all_preserves_unrelated_keys():
    """Verify reset(None) strictly targets configured prefix, preserving other keys."""
    limiter = RedisRateLimiter(key_prefix="ratelimit:custom:")
    mock_client = MagicMock()
    mock_client.scan_iter.return_value = iter(["ratelimit:custom:k1"])

    with patch("src.core.security.get_redis_client", return_value=mock_client):
        limiter.reset(key=None)
        mock_client.scan_iter.assert_called_once_with(match="ratelimit:custom:*", count=100)
        mock_client.delete.assert_called_once_with("ratelimit:custom:k1")
