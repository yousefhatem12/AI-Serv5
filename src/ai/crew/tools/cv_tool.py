from __future__ import annotations
import json
import re
from pydantic import BaseModel, Field
from langchain_community.tools import tool
from src.services import cv_service
from src.db.repositories.candidate_repository import candidate_repository


class CVProfileInput(BaseModel):
    user_id: str = Field(default="default_user", description="The candidate/user ID")


def _clean_user_id(user_id: str) -> str:
    if isinstance(user_id, dict):
        return str(user_id.get("user_id", "default_user"))
    if isinstance(user_id, str) and ("{" in user_id or "user_id" in user_id):
        try:
            cleaned = re.sub(r"```(?:json)?|```", "", user_id).strip()
            parsed = json.loads(cleaned.replace("'", '"'))
            if isinstance(parsed, dict):
                return str(parsed.get("user_id", "default_user"))
        except Exception:
            pass
    return str(user_id)


@tool("Get Candidate CV Profile", args_schema=CVProfileInput)
def get_cv_profile_tool(user_id: str = "default_user") -> dict:
    """
    Returns the profile extracted from the CV: skills, experience, projects,
    and education. Use this as soon as you need to know the user's
    background before making any suggestion.
    """
    user_id = _clean_user_id(user_id)

    if hasattr(cv_service, "get_extracted_profile") and callable(getattr(cv_service, "get_extracted_profile")):
        return cv_service.get_extracted_profile(user_id)
    candidate = candidate_repository.get_candidate(user_id)
    if candidate:
        if hasattr(candidate, "model_dump"):
            return candidate.model_dump()
        if hasattr(candidate, "dict"):
            return candidate.dict()
    return {"user_id": user_id, "skills": [], "experience": [], "education": []}
