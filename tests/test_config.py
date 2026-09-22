from __future__ import annotations
import pytest
from src.core.config import Settings, LLMSettings, get_llm_settings


def test_supported_provider_validation():
    assert LLMSettings.validate_provider("gemini") == "gemini"
    assert LLMSettings.validate_provider("GOOGLE") == "google"
    assert LLMSettings.validate_provider("openai") == "openai"
    assert LLMSettings.validate_provider("groq") == "groq"

    with pytest.raises(ValueError, match="Unsupported LLM provider 'unsupported'"):
        LLMSettings.validate_provider("unsupported")


def test_load_from_env_uses_only_canonical_model(monkeypatch):
    monkeypatch.setattr("src.core.config.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "provider-specific-key")
    monkeypatch.setenv("LLM_MODEL_NAME", "legacy-model")
    loaded = LLMSettings.load_from_env()
    assert loaded.provider is None
    assert loaded.model_name is None
    assert loaded.api_key is None


def test_settings_has_one_canonical_llm_object():
    llm_cfg = LLMSettings(max_tokens=4096, provider="gemini", model_name="gemini-test", api_key="test-key")
    app_cfg = Settings(llm=llm_cfg)
    assert app_cfg.llm is llm_cfg
    assert app_cfg.get_llm_settings() is llm_cfg
    assert app_cfg.llm.max_tokens == 4096
    assert app_cfg.llm.model_name == "gemini-test"


def test_canonical_api_key_is_stored_only_on_llm_settings():
    app_cfg = Settings(
        llm=LLMSettings(provider="openai", model_name="gpt-test", api_key="generic-key")
    )
    assert app_cfg.llm.api_key == "generic-key"
