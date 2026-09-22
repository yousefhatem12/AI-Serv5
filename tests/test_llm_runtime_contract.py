from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.config import LLMSettings, settings
from src.core.llm import get_llm


def test_gemini_provider_maps_to_google_genai_integration():
    old = settings.llm
    settings.llm = LLMSettings(provider="gemini", model_name="opaque-gemini-id", api_key="test-key")
    try:
        with patch("src.core.llm.init_chat_model", return_value=MagicMock()) as init_model:
            get_llm()

        kwargs = init_model.call_args.kwargs
        assert kwargs["model_provider"] == "google_genai"
        assert kwargs["model"] == "opaque-gemini-id"
        assert kwargs["google_api_key"] == "test-key"
    finally:
        settings.llm = old


def test_groq_provider_mapping_does_not_inspect_model_name():
    old = settings.llm
    settings.llm = LLMSettings(provider="groq", model_name="gemini-looking-model", api_key="test-key")
    try:
        with patch("src.core.llm.init_chat_model", return_value=MagicMock()) as init_model:
            get_llm()

        kwargs = init_model.call_args.kwargs
        assert kwargs["model_provider"] == "groq"
        assert kwargs["model"] == "gemini-looking-model"
    finally:
        settings.llm = old


def test_unsupported_provider_fails_before_initialization():
    old = settings.llm
    settings.llm = LLMSettings(provider="ollama", model_name="local-model", api_key="test-key")
    try:
        with patch("src.core.llm.init_chat_model") as init_model:
            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                get_llm()
        init_model.assert_not_called()
    finally:
        settings.llm = old


def test_missing_external_api_key_fails_before_initialization():
    old = settings.llm
    settings.llm = LLMSettings(provider="openai", model_name="gpt-test", api_key="")
    try:
        with patch("src.core.llm.init_chat_model") as init_model:
            with pytest.raises(ValueError, match="LLM_API_KEY is required"):
                get_llm()
        init_model.assert_not_called()
    finally:
        settings.llm = old


def test_provider_initialization_errors_are_actionable():
    old = settings.llm
    settings.llm = LLMSettings(provider="groq", model_name="opaque-model", api_key="test-key")
    try:
        with patch(
            "src.core.llm.init_chat_model",
            side_effect=RuntimeError("provider rejected model"),
        ):
            with pytest.raises(ValueError, match="provider 'groq'.*model 'opaque-model'"):
                get_llm()
    finally:
        settings.llm = old


def test_request_headers_cannot_change_llm_configuration():
    """Ensure HTTP headers like X-LLM-Model / X-LLM-Provider cannot override LLM settings."""
    old_settings = settings.llm
    settings.llm = LLMSettings(
        provider="groq", model_name="llama-3.1-8b-instant", api_key="groq-canonical-key"
    )
    client = TestClient(app)

    try:
        with patch("src.core.llm.init_chat_model", return_value=MagicMock()) as mock_init:
            # Send an endpoint request with attempt to override via headers
            headers = {
                "X-LLM-Model": "malicious-model-override",
                "X-LLM-Provider": "openai",
                "X-LLM-Api-Key": "malicious-key-override",
                "X-LLM-Base-Url": "http://malicious-site.com",
                "X-LLM-Temperature": "0.99",
            }
            response = client.get("/health", headers=headers)
            assert response.status_code == 200

            # Calling get_llm() must strictly use settings.llm, ignoring all request headers
            get_llm()
            call_kwargs = mock_init.call_args.kwargs
            assert call_kwargs["model_provider"] == "groq"
            assert call_kwargs["model"] == "llama-3.1-8b-instant"
            assert call_kwargs["groq_api_key"] == "groq-canonical-key"
    finally:
        settings.llm = old_settings


def test_no_request_scoped_llm_context_exists():
    """Verify that request-scoped LLMContext and DynamicLLMMiddleware are eliminated."""
    import src.core.llm as llm_module
    import src.middleware as middleware_module

    assert not hasattr(llm_module, "get_llm_context")
    assert not hasattr(llm_module, "LLMContext")
    assert not hasattr(middleware_module, "DynamicLLMMiddleware")
    assert not hasattr(middleware_module, "LLMContext")
    assert not hasattr(middleware_module, "get_llm_context")
