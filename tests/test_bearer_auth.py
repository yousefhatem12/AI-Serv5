from __future__ import annotations
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.main import app
from src.core.config import Settings, get_app_settings

client = TestClient(app)


def test_public_routes_accessible_without_token():
    """Docs and health check endpoints must remain accessible without authentication."""
    # Health check
    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "healthy"

    # Root endpoint
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert resp_root.json()["status"] == "healthy"

    # OpenAPI JSON
    resp_openapi = client.get("/openapi.json")
    assert resp_openapi.status_code == 200
    assert "paths" in resp_openapi.json()

    # Swagger Docs
    resp_docs = client.get("/docs")
    assert resp_docs.status_code == 200

    # ReDoc
    resp_redoc = client.get("/redoc")
    assert resp_redoc.status_code == 200


def test_bearer_token_missing_returns_401(monkeypatch):
    """Missing Authorization header on protected routes returns HTTP 401 with required error JSON."""
    settings = get_app_settings()
    monkeypatch.setattr(settings, "enable_api_key_auth", True)
    monkeypatch.setattr(settings, "AI_SERVICE_API_KEY", "test-secret-bearer-key")

    resp = client.post("/api/v1/jobs/analyze", json={"job_description": "Software Engineer"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["detail"] == "Invalid or missing API key"
    assert data["error"] == "UNAUTHORIZED"
    assert data["error_code"] == "UNAUTHORIZED"
    assert "WWW-Authenticate" in resp.headers


def test_bearer_token_invalid_returns_401(monkeypatch):
    """Invalid token returns HTTP 401 with required error JSON."""
    settings = get_app_settings()
    monkeypatch.setattr(settings, "enable_api_key_auth", True)
    monkeypatch.setattr(settings, "AI_SERVICE_API_KEY", "test-secret-bearer-key")

    resp = client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": "Software Engineer"},
        headers={"Authorization": "Bearer wrong-token-xyz"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["detail"] == "Invalid or missing API key"
    assert data["error"] == "UNAUTHORIZED"
    assert data["error_code"] == "UNAUTHORIZED"


def test_bearer_token_valid_grants_access(monkeypatch):
    """Valid Bearer token authorizes the request to protected endpoints."""
    settings = get_app_settings()
    monkeypatch.setattr(settings, "enable_api_key_auth", True)
    monkeypatch.setattr(settings, "AI_SERVICE_API_KEY", "test-secret-bearer-key")

    # Using /api/v1/cv/jobs/nonexistent_job: with valid auth, it reaches the endpoint and returns 404 (not 401)
    resp = client.get(
        "/api/v1/cv/jobs/nonexistent_job",
        headers={"Authorization": "Bearer test-secret-bearer-key"},
    )
    assert resp.status_code == 404  # Reached the endpoint logic


def test_backward_compatible_x_api_key_header(monkeypatch):
    """X-API-Key header continues to work seamlessly alongside Bearer token."""
    settings = get_app_settings()
    monkeypatch.setattr(settings, "enable_api_key_auth", True)
    monkeypatch.setattr(settings, "AI_SERVICE_API_KEY", "test-secret-bearer-key")

    resp = client.get(
        "/api/v1/cv/jobs/nonexistent_job",
        headers={"X-API-Key": "test-secret-bearer-key"},
    )
    assert resp.status_code == 404  # Authorized


def test_env_variable_fallback_behavior(monkeypatch):
    """If AI_SERVICE_API_KEY is missing, Settings falls back to default development key."""
    monkeypatch.delenv("AI_SERVICE_API_KEY", raising=False)
    monkeypatch.delenv("SERVICE_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)

    loaded_settings = Settings.from_env()
    assert loaded_settings.AI_SERVICE_API_KEY == Settings().DEFAULT_AI_SERVICE_API_KEY
    assert loaded_settings.api_key == Settings().DEFAULT_AI_SERVICE_API_KEY


def test_env_variable_custom_configuration(monkeypatch):
    """If AI_SERVICE_API_KEY is configured in env, it is loaded correctly."""
    monkeypatch.setenv("AI_SERVICE_API_KEY", "production-ultra-secret-key-999")

    loaded_settings = Settings.from_env()
    assert loaded_settings.AI_SERVICE_API_KEY == "production-ultra-secret-key-999"
    assert loaded_settings.api_key == "production-ultra-secret-key-999"
