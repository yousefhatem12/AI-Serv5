from __future__ import annotations
"""The single LangChain LLM construction boundary for SkillMatch."""

import json
import logging
import math
import re
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from src.core.config import LLMSettings, settings

logger = logging.getLogger(__name__)

_CREDENTIAL_PROVIDERS = {"gemini", "google", "openai", "groq"}


def estimate_token_count(text: str) -> int:
    """Heuristic token estimation: ~4 characters per token for English & code."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4.0))


def truncate_to_token_limit(
    text: str, max_tokens: int, suffix: str = "\n... [Context truncated to fit limit]"
) -> str:
    """Truncates input text if its estimated token count exceeds max_tokens."""
    if not text or max_tokens <= 0:
        return ""

    current_tokens = estimate_token_count(text)
    if current_tokens <= max_tokens:
        return text

    target_char_count = max(0, (max_tokens * 4) - len(suffix))
    return text[:target_char_count] + suffix


def parse_json_response(raw_text: str) -> dict[str, Any] | list[Any]:
    """Extract one JSON value from a model response without greedy parsing."""
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response received from LLM")
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for block in re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE):
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            continue
    decoder = json.JSONDecoder()
    for idx in (m.start() for m in re.finditer(r"[\{\[]", text)):
        try:
            parsed, _ = decoder.raw_decode(text[idx:])
            return parsed
        except json.JSONDecodeError:
            continue
    repaired = re.sub(r",\s*([\}\]])", r"\1", text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    for idx in (m.start() for m in re.finditer(r"[\{\[]", repaired)):
        try:
            parsed, _ = decoder.raw_decode(repaired[idx:])
            return parsed
        except json.JSONDecodeError:
            continue
    snippet = text[:200] + ("..." if len(text) > 200 else "")
    raise ValueError(f"Failed to extract valid JSON from LLM response: {snippet}")


def get_llm() -> BaseChatModel:
    """Build the configured chat model through one canonical path.

    Configuration source is solely settings.llm (loaded from .env).
    There is no alternative HTTP-request configuration path, no per-call parameter
    overrides, and no provider/model fallback.
    """
    llm_settings = settings.get_llm_settings()

    provider_raw = llm_settings.provider
    if not provider_raw or not provider_raw.strip():
        raise ValueError("LLM_PROVIDER is required; set a supported provider.")
    parsed_provider = LLMSettings.validate_provider(provider_raw)

    model_name = (llm_settings.model_name or "").strip()
    if not model_name:
        raise ValueError("LLM_MODEL is required; set a non-empty model identifier.")

    api_key = (llm_settings.api_key or "").strip() if llm_settings.api_key else None
    if parsed_provider in _CREDENTIAL_PROVIDERS and not api_key:
        raise ValueError(f"LLM_API_KEY is required for provider '{parsed_provider}'")

    langchain_provider = {"gemini": "google_genai", "google": "google_genai"}.get(
        parsed_provider, parsed_provider
    )
    model_kwargs: dict[str, Any] = {
        "max_retries": llm_settings.max_retries,
    }

    # Keep provider-specific constructor names at this boundary; feature code
    # never needs to know which SDK keyword a provider expects.
    if parsed_provider in ("gemini", "google"):
        model_kwargs["timeout"] = llm_settings.timeout
        model_kwargs["google_api_key"] = api_key
        if llm_settings.base_url:
            model_kwargs["client_options"] = {"api_endpoint": llm_settings.base_url}
    elif parsed_provider == "groq":
        model_kwargs["request_timeout"] = llm_settings.timeout
        model_kwargs["groq_api_key"] = api_key
        if llm_settings.base_url:
            model_kwargs["groq_api_base"] = llm_settings.base_url
    else:
        model_kwargs["timeout"] = llm_settings.timeout
        if api_key:
            model_kwargs["api_key"] = api_key
        if llm_settings.base_url:
            model_kwargs["base_url"] = llm_settings.base_url

    logger.debug(
        "Initializing LLM provider=%s model=%s temperature=%s timeout=%s retries=%s",
        parsed_provider,
        model_name,
        llm_settings.temperature,
        llm_settings.timeout,
        llm_settings.max_retries,
    )
    try:
        return init_chat_model(
            model=model_name,
            model_provider=langchain_provider,
            temperature=llm_settings.temperature,
            max_tokens=llm_settings.max_tokens,
            **model_kwargs,
        )
    except Exception as exc:
        raise ValueError(
            f"Failed to initialize LLM provider '{parsed_provider}' with model '{model_name}': {exc}"
        ) from exc
