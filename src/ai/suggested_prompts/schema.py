from __future__ import annotations
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

    @field_validator("prompts", mode="before")
    @classmethod
    def enforce_max_three(cls, v: List[str]) -> List[str]:
        if isinstance(v, list):
            return v[:3]
        return v

