# STEP 2 — Phase 2: Suggested Prompts Feature

> Send this only after Phase 1 is complete and confirmed. Reminder for Antigravity:
> `src/services/*` still must not be touched.

---

## Files to create in this phase

```diff
AI-Serv5/
├── src/
│   ├── ai/
+   │   └── suggested_prompts/
+   │       ├── __init__.py
+   │       ├── schema.py                  # SuggestedPromptsSchema (Pydantic)
+   │       ├── agent_context.py           # AgentType Enum + resolve_active_agent
+   │       ├── generator.py               # Generates the questions with a fast model
+   │       └── fallback.py                # Timeout + exception handling
└── tests/
+   └── test_suggested_prompts.py          # Unit tests for the fallback mechanism
```

> **Note:** if you stubbed a placeholder `AgentType` enum in Phase 1 (to let `src/ai/crew/crew.py` import cleanly), replace it now with the real `src/ai/suggested_prompts/agent_context.py` below, and re-check that `crew.py`'s import still resolves correctly.

---

## Task 2.1 — Schema

**`src/ai/suggested_prompts/schema.py`**
```python
from typing import List
from pydantic import BaseModel, Field, field_validator


class SuggestedPromptsSchema(BaseModel):
    """The shape of the LLM output when generating follow-up questions after each response."""

    prompts: List[str] = Field(
        default_factory=list,
        max_length=3,
        description=(
            "A list of 1 to 3 follow-up questions in first-person phrasing "
            "(e.g., 'How can I...?', 'Could you suggest...?'). Each question "
            "is short (under 15 words), based exclusively on the content of "
            "the last response, and must not repeat the same idea or be a "
            "generic question unrelated to the context."
        ),
    )

    @field_validator("prompts")
    @classmethod
    def enforce_max_three(cls, v: List[str]) -> List[str]:
        return v[:3]
```

---

## Task 2.2 — Agent Context & Intent Identification

**`src/ai/suggested_prompts/agent_context.py`**
```python
from enum import Enum
from pydantic import BaseModel


class AgentType(str, Enum):
    MENTOR = "Mentor Agent"
    ROADMAP = "Roadmap Agent"
    JOB_INSIGHTS = "Job Insights Agent"


class AgentContext(BaseModel):
    agent_type: AgentType
    last_output: str
    conversation_id: str
    user_id: str


AGENT_PROMPT_INSTRUCTIONS: dict[AgentType, str] = {
    AgentType.MENTOR: (
        "Focus the questions on: practical career advice, a specific next "
        "step, or a request for clarification on something mentioned in the "
        "Mentor's response."
    ),
    AgentType.ROADMAP: (
        "Focus the questions on: details of the upcoming milestone, "
        "suggested learning resources, or adjusting the roadmap's "
        "priorities."
    ),
    AgentType.JOB_INSIGHTS: (
        "Focus the questions on: details of the skill gap, the decision to "
        "apply now vs. wait, or other similar jobs."
    ),
}
```
> **Note:** `AgentType` is the single shared source between `crew.py` (Phase 1, determining who responds) and `suggested_prompts` (determining the type of questions) — it must not be duplicated in two places. Double-check `crew.py`'s import of `AgentType` now points here.

---

## Task 2.3 — Dynamic Prompts Generator

**`src/ai/suggested_prompts/generator.py`**
```python
import instructor
from openai import AsyncOpenAI

from .schema import SuggestedPromptsSchema
from .agent_context import AgentType, AGENT_PROMPT_INSTRUCTIONS

_client = instructor.from_openai(AsyncOpenAI())
FAST_MODEL = "gpt-4o-mini"

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
    return await _client.chat.completions.create(
        model=FAST_MODEL,
        response_model=SuggestedPromptsSchema,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=200,
        temperature=0.4,
    )
```

---

## Task 2.4 — Fallback & Error Handling

**`src/ai/suggested_prompts/fallback.py`**
```python
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
        if not result.prompts:
            raise ValueError("Empty prompts returned from LLM")
        return result.prompts
    except Exception as e:
        logger.warning(
            "Suggested prompts failed for agent=%s, reason=%s. Using fallback.",
            agent_type.value, str(e),
        )
        return DEFAULT_FALLBACK_PROMPTS[agent_type]
```

**`tests/test_suggested_prompts.py`**
```python
import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from src.ai.suggested_prompts.agent_context import AgentType
from src.ai.suggested_prompts.schema import SuggestedPromptsSchema
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
```

**Definition of Done (Phase 2):**
- [ ] `pytest -v tests/test_suggested_prompts.py` passes entirely.
- [ ] `get_fallback_with_timeout` can never raise an exception outward.
- [ ] The log records a `warning` every time the fallback kicks in, so the failure rate can be monitored later.
- [ ] `src/ai/crew/crew.py` from Phase 1 now correctly imports the real `AgentType` from this phase's `agent_context.py`.

---

## Before moving to Phase 3

Confirm the tests actually pass (ran, not just written), and that no file inside `src/services/*` was touched. Only send Phase 3 once this is confirmed.
