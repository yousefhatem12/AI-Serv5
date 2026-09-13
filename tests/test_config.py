import pytest
from src.core.config import Settings, LLMSettings, get_llm_settings


def test_settings_provider_and_model_parsing():
    # 1. Standalone model inherits explicitly configured LLM_PROVIDER (never guesses)
    gemini_settings = Settings(LLM_PROVIDER="gemini", LLM_MODEL="gemini-3.5-flash")
    provider, model = gemini_settings.parse_provider_and_model("gemini-3.5-flash")
    assert provider == "gemini"
    assert model == "gemini-3.5-flash"

    groq_settings = Settings(LLM_PROVIDER="groq")
    provider, model = groq_settings.parse_provider_and_model("mixtral-8x7b-32768")
    assert provider == "groq"
    assert model == "mixtral-8x7b-32768"

    # 2. Explicit provider/model namespace prefix
    provider, model = gemini_settings.parse_provider_and_model("openai/gpt-4o-mini")
    assert provider == "openai"
    assert model == "gpt-4o-mini"

    provider, model = gemini_settings.parse_provider_and_model("anthropic/claude-3-5-sonnet")
    assert provider == "anthropic"
    assert model == "claude-3-5-sonnet"

    # 3. Explicit provider argument override
    provider, model = gemini_settings.parse_provider_and_model("custom-model", provider_str="ollama")
    assert provider == "ollama"
    assert model == "custom-model"


def test_unified_max_tokens_and_defaults():
    """Verify single source of truth for max_tokens and core LLM parameters."""
    llm_cfg = LLMSettings(LLM_MAX_TOKENS=4096)
    assert llm_cfg.max_tokens == 4096

    app_cfg = Settings(LLM_MAX_TOKENS=4096)
    assert app_cfg.LLM_MAX_TOKENS == 4096

    derived_llm = app_cfg.get_llm_settings()
    assert derived_llm.max_tokens == 4096
    assert derived_llm.provider == app_cfg.LLM_PROVIDER
    assert derived_llm.model_name == app_cfg.LLM_MODEL_NAME


def test_settings_api_key_resolution():
    settings = Settings(
        GROQ_API_KEY="groq_key_123",
        OPENAI_API_KEY="openai_key_456",
        ANTHROPIC_API_KEY="anthropic_key_789",
        GEMINI_API_KEY="gemini_key_abc"
    )
    assert settings.get_api_key("groq") == "groq_key_123"
    assert settings.get_api_key("openai") == "openai_key_456"
    assert settings.get_api_key("anthropic") == "anthropic_key_789"
    assert settings.get_api_key("gemini") == "gemini_key_abc"

    # Generic primary override takes priority
    settings_with_override = Settings(
        LLM_API_KEY="generic_override_key",
        GROQ_API_KEY="groq_key_123"
    )
    assert settings_with_override.get_api_key("groq") == "generic_override_key"
    assert settings_with_override.get_api_key("gemini") == "generic_override_key"
