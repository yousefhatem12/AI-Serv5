from __future__ import annotations
import asyncio
import logging
from typing import List

from .agent_context import AgentType
from .generator import generate_suggested_prompts

logger = logging.getLogger("suggested_prompts")

DEFAULT_FALLBACK_PROMPTS: dict[AgentType, List[str]] = {
    AgentType.MENTOR: [
        "What's the most important practical step I should take this week?",
        "Can you explain in more detail how to develop this skill?",
        "What are the most likely interview questions in this field?",
    ],
    AgentType.ROADMAP: [
        "What's the most important milestone I should start with?",
        "Can you suggest learning resources for a specific skill?",
        "Can I adjust the roadmap's priorities?",
    ],
    AgentType.JOB_INSIGHTS: [
        "What's my biggest skill gap relative to this job?",
        "Should I apply now or wait?",
        "Are there other similar jobs that would suit me?",
    ],
}


async def get_fallback_with_timeout(
    agent_type: AgentType, agent_answer: str, timeout_seconds: float = 2.5
) -> List[str]:
    try:
        result = await asyncio.wait_for(
            generate_suggested_prompts(agent_type, agent_answer),
            timeout=timeout_seconds,
        )
        if not result or not getattr(result, "prompts", None):
            raise ValueError("Empty prompts returned from LLM")
        return result.prompts
    except Exception as e:
        logger.warning(
            "Suggested prompts failed for agent=%s, reason=%s. Using fallback.",
            agent_type.value, str(e),
        )
        return DEFAULT_FALLBACK_PROMPTS[agent_type]
