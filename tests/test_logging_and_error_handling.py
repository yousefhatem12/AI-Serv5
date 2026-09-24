import logging
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.main import app
from src.core.logging import setup_logging, get_logger

client = TestClient(app)
client_no_raise = TestClient(app, raise_server_exceptions=False)


def test_setup_logging_initialization():
    """Verify logging is configured properly with desired levels and formatters."""
    setup_logging("DEBUG")
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG

    logger = get_logger("test_module")
    assert logger.name == "test_module"

    # Reset back to INFO
    setup_logging("INFO")
    assert logging.getLogger().level == logging.INFO


def test_repeated_setup_logging_does_not_duplicate_handlers():
    """Verify multiple setup_logging calls do not add duplicate handlers to root logger."""
    setup_logging("INFO")
    root_logger = logging.getLogger()
    initial_count = len(root_logger.handlers)

    # Repeated invocations with different levels
    setup_logging("DEBUG")
    setup_logging("INFO")
    setup_logging("WARNING")

    assert len(root_logger.handlers) == initial_count
    setup_logging("INFO")


def test_setup_logging_respects_log_level():
    """Verify root logger level reflects the requested log level string."""
    setup_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG

    setup_logging("WARNING")
    assert logging.getLogger().level == logging.WARNING

    setup_logging("INFO")
    assert logging.getLogger().level == logging.INFO


def test_third_party_logger_suppression_when_level_above_debug():
    """Verify noisy third-party loggers are set to WARNING when level > DEBUG."""
    setup_logging("INFO")
    for noisy_lib in ("httpx", "httpcore", "urllib3", "asyncio", "watchfiles"):
        assert logging.getLogger(noisy_lib).level == logging.WARNING


def test_third_party_loggers_not_suppressed_in_debug():
    """Verify third-party loggers are not forced to WARNING when level is DEBUG."""
    logging.getLogger("httpx").setLevel(logging.DEBUG)
    setup_logging("DEBUG")
    assert logging.getLogger("httpx").level == logging.DEBUG
    setup_logging("INFO")


def test_get_logger_returns_named_logger():
    """Verify get_logger returns an instance of logging.Logger with the given name."""
    log = get_logger("my_custom_service")
    assert isinstance(log, logging.Logger)
    assert log.name == "my_custom_service"


def test_safe_error_message_redaction():
    """Verify _safe_error_message redacts configured secrets from error strings."""
    from src.integrations.jooble.ingestion import _safe_error_message

    fake_secret = "test-secret-token-xyz-12345"
    with patch("src.integrations.jooble.ingestion.settings.JOOBLE_API_KEY", fake_secret):
        exc = RuntimeError(f"Failed to connect to API with key {fake_secret}")
        redacted = _safe_error_message(exc)
        assert fake_secret not in redacted
        assert "[REDACTED]" in redacted


@patch("src.services.matching_service.matching_service.analyze_skill_gap")
def test_unhandled_server_exception_handler_500(mock_analyze):
    """Verify uncaught unexpected exceptions return 500 with INTERNAL_SERVER_ERROR."""
    mock_analyze.side_effect = RuntimeError("Unexpected internal crash")

    payload = {
        "job_id": "job_crash",
        "candidate_id": "cand_crash",
        "job_requirements": [{"skill_name": "Python"}],
        "candidate_profile": {"skills": ["Python"]}
    }
    response = client_no_raise.post("/api/v1/matches/analyze", json=payload)
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "INTERNAL_SERVER_ERROR"
    assert "unexpected internal server error" in body["detail"].lower()


@patch("src.services.matching_service.matching_service.analyze_skill_gap")
def test_provider_neutral_error_bubbles_to_500(mock_analyze):
    """Verify provider-neutral runtime errors bubble up to standard 500 handler."""
    mock_analyze.side_effect = Exception("Upstream model provider error")

    payload = {
        "job_id": "job_provider_err",
        "candidate_id": "cand_provider_err",
        "job_requirements": [{"skill_name": "Python"}],
        "candidate_profile": {"skills": ["Python"]}
    }
    response = client_no_raise.post("/api/v1/matches/analyze", json=payload)
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "INTERNAL_SERVER_ERROR"
    assert "unexpected internal server error" in body["detail"].lower()
