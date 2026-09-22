from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.config import LLMSettings, settings
from src.core.llm import estimate_token_count, get_llm, truncate_to_token_limit


def test_get_llm_uses_canonical_settings_without_network_calls():
    old_settings = settings.llm
    settings.llm = LLMSettings(
        provider="groq", model_name="llama-test", api_key="test-key"
    )
    try:
        with patch("src.core.llm.init_chat_model", return_value=MagicMock()) as init_model:
            get_llm()
        kwargs = init_model.call_args.kwargs
        assert kwargs["model_provider"] == "groq"
        assert kwargs["model"] == "llama-test"
        assert kwargs["groq_api_key"] == "test-key"
    finally:
        settings.llm = old_settings


def test_get_llm_missing_provider_fails():
    old_settings = settings.llm
    settings.llm = LLMSettings(model_name="test-model", api_key="test-key")
    try:
        with patch("src.core.llm.init_chat_model") as init_model:
            with pytest.raises(ValueError, match="LLM_PROVIDER is required"):
                get_llm()
        init_model.assert_not_called()
    finally:
        settings.llm = old_settings


def test_get_llm_invalid_provider_fails():
    old_settings = settings.llm
    settings.llm = LLMSettings(provider="unsupported-provider", model_name="test-model", api_key="test-key")
    try:
        with patch("src.core.llm.init_chat_model") as init_model:
            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                get_llm()
        init_model.assert_not_called()
    finally:
        settings.llm = old_settings


def test_get_llm_missing_model_fails():
    old_settings = settings.llm
    settings.llm = LLMSettings(provider="groq", api_key="test-key")
    try:
        with patch("src.core.llm.init_chat_model") as init_model:
            with pytest.raises(ValueError, match="LLM_MODEL is required"):
                get_llm()
        init_model.assert_not_called()
    finally:
        settings.llm = old_settings


def test_get_llm_missing_api_key_fails_for_credential_provider():
    old_settings = settings.llm
    settings.llm = LLMSettings(provider="openai", model_name="gpt-4o", api_key=None)
    try:
        with patch("src.core.llm.init_chat_model") as init_model:
            with pytest.raises(ValueError, match="LLM_API_KEY is required for provider 'openai'"):
                get_llm()
        init_model.assert_not_called()
    finally:
        settings.llm = old_settings


def test_get_llm_no_silent_fallback():
    old_settings = settings.llm
    settings.llm = LLMSettings(provider="gemini", model_name="nonexistent-gemini-model", api_key="gem-key")
    try:
        with patch("src.core.llm.init_chat_model", return_value=MagicMock()) as init_model:
            get_llm()
        kwargs = init_model.call_args.kwargs
        # Must strictly preserve exact provider and exact model name without fallback
        assert kwargs["model_provider"] == "google_genai"
        assert kwargs["model"] == "nonexistent-gemini-model"
    finally:
        settings.llm = old_settings


def test_switching_configuration_changes_model_and_provider():
    old_settings = settings.llm
    try:
        settings.llm = LLMSettings(provider="gemini", model_name="gemini-2.5-flash", api_key="gem-key")
        with patch("src.core.llm.init_chat_model", return_value=MagicMock()) as init_gemini:
            get_llm()
        assert init_gemini.call_args.kwargs["model"] == "gemini-2.5-flash"
        assert init_gemini.call_args.kwargs["model_provider"] == "google_genai"

        settings.llm = LLMSettings(provider="groq", model_name="llama-3.3-70b", api_key="groq-key")
        with patch("src.core.llm.init_chat_model", return_value=MagicMock()) as init_groq:
            get_llm()
        assert init_groq.call_args.kwargs["model"] == "llama-3.3-70b"
        assert init_groq.call_args.kwargs["model_provider"] == "groq"
    finally:
        settings.llm = old_settings


def test_token_estimation_and_truncation():
    text = "Hello world"
    assert estimate_token_count(text) > 0
    assert truncate_to_token_limit(text, max_tokens=100) == text

    long_text = "word " * 500
    truncated = truncate_to_token_limit(long_text, max_tokens=20)
    assert len(truncated) < len(long_text)
    assert "truncated" in truncated
