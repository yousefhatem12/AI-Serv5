import logging
from typing import TypeVar, Type, Optional, Any

from pydantic import BaseModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from src.ai.adapters.base import BaseLLMAdapter
from src.core.config import settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiAdapter(BaseLLMAdapter):
    """
    Adapter for Google Gemini models via LangChain's ChatGoogleGenerativeAI.

    Supports both the google-generativeai SDK path (model_provider='google_genai')
    and the OpenAI-compatible endpoint (base_url override).  The adapter is also
    reachable via the 'gemini' provider alias used throughout the codebase.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ):
        self._model_id = model or "gemini-3.6-flash"
        # Strip provider prefix if caller passed "gemini/gemini-3.6-flash"
        if "/" in self._model_id:
            self._model_id = self._model_id.split("/", 1)[1]

        resolved_api_key = api_key or settings.get_api_key("gemini") or "not-configured"

        model_kwargs: dict = {
            "google_api_key": resolved_api_key,
            "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
            "max_output_tokens": settings.LLM_MAX_TOKENS,
            "max_retries": settings.LLM_MAX_RETRIES,
        }
        if base_url:
            model_kwargs["transport"] = "rest"
            model_kwargs["client_options"] = {"api_endpoint": base_url}

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
            self._llm: BaseChatModel = ChatGoogleGenerativeAI(
                model=self._model_id,
                **model_kwargs,
            )
            logger.debug(
                "GeminiAdapter initialised: model=%s via langchain-google-genai",
                self._model_id,
            )
        except ImportError:
            # Fallback: use LangChain's generic init_chat_model with google_genai provider
            from langchain.chat_models import init_chat_model  # type: ignore
            self._llm = init_chat_model(
                model=self._model_id,
                model_provider="google_genai",
                temperature=model_kwargs.get("temperature"),
                max_tokens=settings.LLM_MAX_TOKENS,
                google_api_key=resolved_api_key,
            )
            logger.debug(
                "GeminiAdapter initialised: model=%s via init_chat_model fallback",
                self._model_id,
            )

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_id

    def get_underlying_model(self) -> BaseChatModel:
        return self._llm

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("user", prompt))
        prompt_tmpl = ChatPromptTemplate.from_messages(messages)
        formatted = prompt_tmpl.format_messages()
        res = await self._llm.ainvoke(formatted)
        return str(res.content)

    async def generate_structured(
        self,
        schema: Type[T],
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> T:
        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("user", prompt))
        prompt_tmpl = ChatPromptTemplate.from_messages(messages)
        formatted = prompt_tmpl.format_messages()
        structured_llm = self._llm.with_structured_output(schema)
        return await structured_llm.ainvoke(formatted)
