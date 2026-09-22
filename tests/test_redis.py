from __future__ import annotations
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.core.redis import RedisManager, get_redis_client, is_redis_available, redis_manager
from src.core.security import RedisRateLimiter, HybridRateLimiter
from src.core.cache import CacheService, cache_service
from src.workers.dispatcher import task_dispatcher

client = TestClient(app)
REDIS_AVAILABLE = is_redis_available(force_refresh=True)


redis_required = pytest.mark.skipif(
    not REDIS_AVAILABLE,
    reason="Redis server is not available in this environment",
)

@pytest.fixture(autouse=True)
def clean_test_keys():
    """Flushes test Redis keys before and after each test."""
    if is_redis_available():
        r = get_redis_client()
        keys = r.keys("test:*") + r.keys("ratelimit:test:*") + r.keys("skillmatch:cache:test:*")
        if keys:
            r.delete(*keys)
    yield
    if is_redis_available():
        r = get_redis_client()
        keys = r.keys("test:*") + r.keys("ratelimit:test:*") + r.keys("skillmatch:cache:test:*")
        if keys:
            r.delete(*keys)

@redis_required
def test_redis_connection_and_ping():
    """Verify Redis connection pool is functional and responds to PING."""
    assert is_redis_available(force_refresh=True) is True
    r = get_redis_client()
    assert r.ping() is True

@redis_required
def test_redis_rate_limiter_sliding_window():
    """Verify Redis-backed distributed rate limiter maintains sliding window."""
    limiter = RedisRateLimiter(key_prefix="ratelimit:test:")
    client_key = "client_alpha"

    # Allow 3 requests per 2 seconds
    allowed, remaining, _ = limiter.check(client_key, max_requests=3, window_seconds=2)
    assert allowed is True
    assert remaining == 2

    allowed, remaining, _ = limiter.check(client_key, max_requests=3, window_seconds=2)
    assert allowed is True
    assert remaining == 1

    allowed, remaining, _ = limiter.check(client_key, max_requests=3, window_seconds=2)
    assert allowed is True
    assert remaining == 0

    # 4th request should be throttled
    allowed, remaining, retry_after = limiter.check(client_key, max_requests=3, window_seconds=2)
    assert allowed is False
    assert remaining == 0
    assert retry_after >= 1

    # Reset clears Redis keys
    limiter.reset(client_key)
    allowed, remaining, _ = limiter.check(client_key, max_requests=3, window_seconds=2)
    assert allowed is True
    assert remaining == 2

def test_hybrid_rate_limiter_failover():
    """Verify HybridRateLimiter gracefully fails over to memory if Redis encounters an error."""
    hybrid = HybridRateLimiter()

    with patch("src.core.security.is_redis_available", return_value=False):
        allowed, remaining, _ = hybrid.check("failover_client", max_requests=2, window_seconds=5)
        assert allowed is True
        assert remaining == 1

        allowed, remaining, _ = hybrid.check("failover_client", max_requests=2, window_seconds=5)
        assert allowed is True
        assert remaining == 0

        # Throttled in memory
        allowed, remaining, retry_after = hybrid.check("failover_client", max_requests=2, window_seconds=5)
        assert allowed is False
        assert retry_after >= 1

@redis_required
def test_cache_service_redis_operations():
    """Verify CacheService correctly stores, retrieves, and evicts from Redis."""
    cache = CacheService(key_prefix="skillmatch:cache:test:")
    key = "user_summary_101"
    payload = {"skills": ["Python", "Docker"], "score": 92.5}

    # Set and Get
    assert cache.set(key, payload, ttl_seconds=10) is True
    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved["score"] == 92.5
    assert "Docker" in retrieved["skills"]

    # Delete
    assert cache.delete(key) is True
    assert cache.get(key) is None

def test_cache_service_memory_fallback():
    """Verify CacheService falls back to memory cache when Redis is unavailable."""
    cache = CacheService(key_prefix="skillmatch:cache:test:")
    key = "fallback_key"
    payload = {"status": "ok"}

    with patch("src.core.cache.is_redis_available", return_value=False):
        assert cache.set(key, payload, ttl_seconds=10) is True
        cached = cache.get(key)
        assert cached == payload

        cache.delete(key)
        assert cache.get(key) is None

@redis_required
def test_task_dispatcher_with_redis_available():
    """Verify dispatcher attempts Celery queueing when Redis is verified available."""
    mock_task = MagicMock()
    mock_task.id = "celery_task_12345"

    with patch("src.workers.dispatcher.is_redis_available", return_value=True), \
         patch("src.workers.dispatcher.async_analyze_skill_gap.delay", return_value=mock_task):
        res = task_dispatcher.dispatch_skill_gap_analysis({"job_id": "j1"}, use_celery=True)
        assert res["status"] == "queued"
        assert res["mode"] == "celery"
        assert res["task_id"] == "celery_task_12345"

def test_task_dispatcher_fast_sync_fallback_when_redis_offline():
    """Verify dispatcher immediately runs synchronously when Redis is offline."""
    with patch("src.workers.dispatcher.is_redis_available", return_value=False), \
         patch("src.workers.dispatcher.async_analyze_skill_gap", return_value={"job_id": "j1", "score": 80.0}):
        res = task_dispatcher.dispatch_skill_gap_analysis({"job_id": "j1"}, use_celery=True)
        assert res["status"] == "completed"
        assert res["mode"] == "sync"
        assert res["result"]["score"] == 80.0

def test_health_check_reports_redis_status():
    """Verify /health endpoint returns real-time Redis connectivity information."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "redis" in data
    assert data["redis"]["status"] in ("connected", "unavailable")
    assert "url" in data["redis"]


def test_redis_manager_lazy_pool_initialization():
    """Verify RedisManager pool starts as None and is created on first access."""
    manager = RedisManager()
    assert manager._pool is None
    with patch("redis.ConnectionPool.from_url") as mock_pool_factory:
        mock_pool = MagicMock()
        mock_pool_factory.return_value = mock_pool
        pool = manager.get_pool()
        assert pool is mock_pool
        assert manager._pool is mock_pool
        mock_pool_factory.assert_called_once()


def test_redis_manager_pool_reuse():
    """Verify repeated get_pool() calls return the same pool and get_client() uses that shared pool."""
    manager = RedisManager()
    with patch("redis.ConnectionPool.from_url") as mock_pool_factory, \
         patch("redis.Redis") as mock_redis_factory:
        mock_pool = MagicMock()
        mock_pool_factory.return_value = mock_pool

        pool1 = manager.get_pool()
        pool2 = manager.get_pool()
        assert pool1 is pool2
        mock_pool_factory.assert_called_once()

        manager.get_client()
        mock_redis_factory.assert_called_once_with(connection_pool=pool1)


def test_redis_manager_close_behavior():
    """Verify close() disconnects pool and resets pool, health status, and health check timestamp."""
    manager = RedisManager()
    mock_pool = MagicMock()
    manager._pool = mock_pool
    manager._last_health_status = True
    manager._last_health_check_time = 123456.78

    manager.close()
    mock_pool.disconnect.assert_called_once()
    assert manager._pool is None
    assert manager._last_health_status is False
    assert manager._last_health_check_time == 0.0


def test_redis_manager_health_status_cache_behavior():
    """Verify health status is cached and reused within the TTL."""
    manager = RedisManager()
    manager._health_check_cache_ttl = 30.0

    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch.object(manager, "get_client", return_value=mock_client):
        # First call performs ping
        status1 = manager.is_available()
        assert status1 is True
        assert mock_client.ping.call_count == 1

        # Second call within TTL does not re-ping
        status2 = manager.is_available()
        assert status2 is True
        assert mock_client.ping.call_count == 1


def test_redis_manager_force_refresh_bypasses_cache():
    """Verify force_refresh=True bypasses cached status and performs a fresh ping."""
    manager = RedisManager()
    manager._health_check_cache_ttl = 30.0
    manager._last_health_status = False
    manager._last_health_check_time = time.time()  # Recent check within TTL

    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch.object(manager, "get_client", return_value=mock_client):
        # Normal call returns cached False without pinging
        assert manager.is_available(force_refresh=False) is False
        mock_client.ping.assert_not_called()

        # Force refresh performs fresh ping and updates status
        assert manager.is_available(force_refresh=True) is True
        mock_client.ping.assert_called_once()
        assert manager._last_health_status is True


def test_cache_service_flush_uses_scan_iter_and_never_keys():
    """Verify flush() uses non-blocking scan_iter and never calls blocking keys()."""
    cache = CacheService(key_prefix="skillmatch:cache:test:")
    cache._memory_cache["local_k"] = ("val", time.time() + 100)

    mock_client = MagicMock()
    mock_client.scan_iter.return_value = iter(["skillmatch:cache:test:1", "skillmatch:cache:test:2"])

    with patch("src.core.cache.is_redis_available", return_value=True), \
         patch("src.core.cache.get_redis_client", return_value=mock_client):
        cache.flush()

        # Keys must NEVER be called
        mock_client.keys.assert_not_called()
        # scan_iter must be called with the exact prefix pattern and batch count 100
        mock_client.scan_iter.assert_called_once_with(match="skillmatch:cache:test:*", count=100)
        # Delete called with matching keys
        mock_client.delete.assert_called_once_with("skillmatch:cache:test:1", "skillmatch:cache:test:2")
        # Memory cache cleared
        assert len(cache._memory_cache) == 0


def test_cache_service_flush_batched_multi_batch_and_partial():
    """Verify flush() deletes in batches of 100 and deletes any final partial batch."""
    cache = CacheService(key_prefix="skillmatch:cache:test:")
    keys_250 = [f"skillmatch:cache:test:k_{i}" for i in range(250)]

    mock_client = MagicMock()
    mock_client.scan_iter.return_value = iter(keys_250)

    with patch("src.core.cache.is_redis_available", return_value=True), \
         patch("src.core.cache.get_redis_client", return_value=mock_client):
        cache.flush()

        assert mock_client.delete.call_count == 3
        # First batch: 100 keys
        call1_args = mock_client.delete.call_args_list[0][0]
        assert len(call1_args) == 100
        assert call1_args == tuple(keys_250[:100])

        # Second batch: 100 keys
        call2_args = mock_client.delete.call_args_list[1][0]
        assert len(call2_args) == 100
        assert call2_args == tuple(keys_250[100:200])

        # Third batch (final partial): 50 keys
        call3_args = mock_client.delete.call_args_list[2][0]
        assert len(call3_args) == 50
        assert call3_args == tuple(keys_250[200:250])


def test_cache_service_flush_preserves_unrelated_redis_keys():
    """Verify flush only targets the configured prefix, preserving other keys."""
    cache = CacheService(key_prefix="skillmatch:cache:app:")

    mock_client = MagicMock()
    mock_client.scan_iter.return_value = iter(["skillmatch:cache:app:k1"])

    with patch("src.core.cache.is_redis_available", return_value=True), \
         patch("src.core.cache.get_redis_client", return_value=mock_client):
        cache.flush()

        # Pattern strictly bound to cache prefix
        mock_client.scan_iter.assert_called_once_with(match="skillmatch:cache:app:*", count=100)
        mock_client.delete.assert_called_once_with("skillmatch:cache:app:k1")


def test_cache_service_memory_fallback_ttl_expiration():
    """Verify memory fallback expires entries when time surpasses TTL."""
    cache = CacheService(key_prefix="skillmatch:cache:test:")

    with patch("src.core.cache.is_redis_available", return_value=False):
        cache.set("short_lived", {"data": 123}, ttl_seconds=1)

        # Before expiry
        with patch("time.time", return_value=time.time()):
            assert cache.get("short_lived") == {"data": 123}

        # After expiry (jump 5 seconds into future)
        future_time = time.time() + 5.0
        with patch("time.time", return_value=future_time):
            assert cache.get("short_lived") is None
            assert "short_lived" not in cache._memory_cache


def test_cache_service_delete_removes_both_memory_and_redis():
    """Verify delete() removes entry from local memory cache and calls redis delete."""
    cache = CacheService(key_prefix="skillmatch:cache:test:")
    mock_client = MagicMock()
    mock_client.delete.return_value = 1

    with patch("src.core.cache.is_redis_available", return_value=True), \
         patch("src.core.cache.get_redis_client", return_value=mock_client):
        cache.set("target_key", {"msg": "hello"}, ttl_seconds=60)
        assert "target_key" in cache._memory_cache

        deleted = cache.delete("target_key")
        assert deleted is True
        assert "target_key" not in cache._memory_cache
        mock_client.delete.assert_called_once_with("skillmatch:cache:test:target_key")


def test_cache_service_redis_unavailable_retains_memory_fallback():
    """Verify CacheService works smoothly in pure in-memory mode when Redis is offline."""
    cache = CacheService(key_prefix="skillmatch:cache:test:")

    with patch("src.core.cache.is_redis_available", return_value=False):
        # set
        assert cache.set("offline_k", {"v": 42}, ttl_seconds=300) is True
        # get
        assert cache.get("offline_k") == {"v": 42}
        # delete
        assert cache.delete("offline_k") is True
        assert cache.get("offline_k") is None
        # flush
        cache.set("offline_k2", "v2", ttl_seconds=300)
        assert len(cache._memory_cache) == 1
        cache.flush()
        assert len(cache._memory_cache) == 0
