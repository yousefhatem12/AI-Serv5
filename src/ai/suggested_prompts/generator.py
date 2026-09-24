from __future__ import annotations
from src.core.llm import get_llm
from .schema import SuggestedPromptsSchema
from .agent_context import AgentType, AGENT_PROMPT_INSTRUCTIONS

SYSTEM_PROMPT = """
You are an assistant specialized in generating follow-up questions for
SkillMatch platform users, based on the last response they received from one
of the AI Agents. Your only job is to return a list of short first-person
questions, with no extra text or explanation.
"""


async def generate_suggested_prompts(
    agent_type: AgentType, agent_answer: str
) -> SuggestedPromptsSchema:
    agent_guidance = AGENT_PROMPT_INSTRUCTIONS[agent_type]
    user_prompt = f"""
Agent type: {agent_type.value}
Specific guidance: {agent_guidance}

Last response from the Agent:
---
{agent_answer}
---

Generate 3 appropriate follow-up questions per the conditions above.
"""
    llm = get_llm(temperature=0.4, max_tokens=200)
    structured_llm = llm.with_structured_output(SuggestedPromptsSchema)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    result = await structured_llm.ainvoke(messages)
    if isinstance(result, dict):
        return SuggestedPromptsSchema(**result)
    return result
