from __future__ import annotations
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from src.ai.suggested_prompts.agent_context import AgentType, AgentContext
from src.ai.suggested_prompts.schema import SuggestedPromptsSchema
from src.ai.suggested_prompts.generator import generate_suggested_prompts
from src.ai.suggested_prompts.fallback import (
    get_fallback_with_timeout,
    DEFAULT_FALLBACK_PROMPTS,
)


@pytest.mark.asyncio
async def test_fallback_triggers_on_timeout():
    async def slow(*a, **k):
        await asyncio.sleep(5)

    with patch("src.ai.suggested_prompts.fallback.generate_suggested_prompts", side_effect=slow):
        result = await get_fallback_with_timeout(AgentType.MENTOR, "x", timeout_seconds=0.1)
        assert result == DEFAULT_FALLBACK_PROMPTS[AgentType.MENTOR]


@pytest.mark.asyncio
async def test_fallback_triggers_on_exception():
    with patch(
        "src.ai.suggested_prompts.fallback.generate_suggested_prompts",
        new=AsyncMock(side_effect=RuntimeError("LLM error")),
    ):
        result = await get_fallback_with_timeout(AgentType.ROADMAP, "x")
        assert result == DEFAULT_FALLBACK_PROMPTS[AgentType.ROADMAP]


@pytest.mark.asyncio
async def test_successful_generation():
    mocked = SuggestedPromptsSchema(prompts=["q1", "q2", "q3"])
    with patch(
        "src.ai.suggested_prompts.fallback.generate_suggested_prompts",
        new=AsyncMock(return_value=mocked),
    ):
        result = await get_fallback_with_timeout(AgentType.MENTOR, "x")
        assert result == ["q1", "q2", "q3"]


@pytest.mark.asyncio
async def test_never_raises():
    with patch(
        "src.ai.suggested_prompts.fallback.generate_suggested_prompts",
        new=AsyncMock(side_effect=TimeoutError()),
    ):
        try:
            result = await get_fallback_with_timeout(AgentType.MENTOR, "x")
        except Exception:
            pytest.fail("get_fallback_with_timeout must swallow any exception")
        assert len(result) == 3


def test_schema_enforces_max_three_prompts():
    schema = SuggestedPromptsSchema(prompts=["q1", "q2", "q3", "q4", "q5"])
    assert len(schema.prompts) == 3
    assert schema.prompts == ["q1", "q2", "q3"]


@pytest.mark.asyncio
async def test_generator_structured_llm_invocation():
    mock_llm = MagicMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke.return_value = SuggestedPromptsSchema(
        prompts=["What is step 1?", "How to prepare?", "Any tips?"]
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("src.ai.suggested_prompts.generator.get_llm", return_value=mock_llm):
        res = await generate_suggested_prompts(AgentType.MENTOR, "You should start by studying Python.")
        assert isinstance(res, SuggestedPromptsSchema)
        assert len(res.prompts) == 3
        assert res.prompts[0] == "What is step 1?"
        mock_llm.with_structured_output.assert_called_once_with(SuggestedPromptsSchema)
        mock_structured.ainvoke.assert_awaited_once()
