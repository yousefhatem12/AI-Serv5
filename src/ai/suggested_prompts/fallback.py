from __future__ import annotations
import asyncio
import logging
from typing import List

from .agent_context import AgentType
from .generator import generate_suggested_prompts

logger = logging.getLogger("suggested_prompts")

DEFAULT_FALLBACK_PROMPTS: dict[AgentType, List[str]] = {
    AgentType.MENTOR: [
        "How should I structure my target role and timeline into concrete milestones?",
        "What lessons should I capture from my latest application or interview?",
        "What evidence or portfolio project should I add to prove this skill?",
    ],
    AgentType.ROADMAP: [
        "What should my weekly action plan look like for this milestone?",
        "How should I reprioritize my roadmap after completing this project?",
        "Which skill gap should I tackle first this week?",
    ],
    AgentType.JOB_INSIGHTS: [
        "How do my verified skills compare against this job's requirements?",
        "Which topics should I prioritize practicing for interview readiness?",
        "Should I apply now or focus on closing these specific skill gaps first?",
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
