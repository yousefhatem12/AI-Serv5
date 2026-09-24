from __future__ import annotations
import json
import re
from typing import Optional
from pydantic import BaseModel, Field
from langchain_community.tools import tool
from src.services import interview_service
from src.services.interview_service import interview_service as default_interview_service


class InterviewPrepInput(BaseModel):
    user_id: str = Field(default="default_user", description="The candidate/user ID")
    job_id: str = Field(default="general_interview", description="The target job ID or role title")


def _clean_interview_args(user_id: str, job_id: str = "general_interview") -> tuple[str, str]:
    if isinstance(user_id, dict):
        return str(user_id.get("user_id", "default_user")), str(user_id.get("job_id", job_id))
    if isinstance(user_id, str) and ("{" in user_id or "job_id" in user_id):
        try:
            cleaned = re.sub(r"```(?:json)?|```", "", user_id).strip()
            parsed = json.loads(cleaned.replace("'", '"'))
            if isinstance(parsed, dict):
                u = parsed.get("user_id", "default_user")
                j = parsed.get("job_id", job_id)
                return str(u), str(j)
        except Exception:
            pass
    return str(user_id), str(job_id)


@tool("Get Interview Preparation", args_schema=InterviewPrepInput)
def get_interview_prep_tool(user_id: str = "default_user", job_id: str = "general_interview") -> dict:
    """
    Generates interview questions and study topics related to a specific job
    and the user's gaps. Use this when interview preparation is requested.
    """
    user_id, job_id = _clean_interview_args(user_id, job_id)

    if hasattr(interview_service, "generate_prep") and callable(getattr(interview_service, "generate_prep")):
        return interview_service.generate_prep(user_id=user_id, job_id=job_id)
    if hasattr(default_interview_service, "generate_prep") and callable(getattr(default_interview_service, "generate_prep")):
        return default_interview_service.generate_prep(user_id=user_id, job_id=job_id)
    return {
        "candidate_id": user_id,
        "job_id": job_id,
        "questions": ["What is your experience with system design?", "Explain RESTful API principles."],
        "study_topics": ["Architecture", "System Scaling"],
    }
