from __future__ import annotations
from pydantic import BaseModel


class MentorChatRequest(BaseModel):
    message: str
    conversation_id: str
    user_id: str


class MentorChatEvent(BaseModel):
    type: str  # "token" | "suggested_prompts" | "error"
    content: str | None = None
    agent: str | None = None
    prompts: list[str] | None = None
