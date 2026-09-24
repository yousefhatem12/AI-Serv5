from __future__ import annotations
from pydantic import BaseModel


class MentorChatRequest(BaseModel):
    message: str
    conversation_id: str
    user_id: str
    job_id: str | None = None
    target_role: str | None = None
    career_preferences: dict | None = None
    saved_jobs: list[str] | list[dict] | None = None
    applied_jobs: list[dict] | None = None
    application_statuses: list[dict] | None = None
    match_reports: list[dict] | None = None
    user_notes: list[str] | None = None
    current_milestones: list[str] | None = None


class MentorChatEvent(BaseModel):
    type: str  # "token" | "suggested_prompts" | "error"
    content: str | None = None
    agent: str | None = None
    prompts: list[str] | None = None
