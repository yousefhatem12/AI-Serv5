from __future__ import annotations
import json
import re
from pydantic import BaseModel, Field
from langchain_community.tools import tool
from src.services import matching_service
from src.services.matching_service import matching_service as default_matching_service


class JobMatchInput(BaseModel):
    user_id: str = Field(default="default_user", description="The candidate/user ID")
    job_id: str = Field(default="default_job", description="The job ID to match against")


def _clean_match_args(user_id: str, job_id: str = "default_job") -> tuple[str, str]:
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


@tool("Get Job Match & Skill Gaps", args_schema=JobMatchInput)
def get_job_match_tool(user_id: str = "default_user", job_id: str = "default_job") -> dict:
    """
    Calculates the match percentage between the user and a specific job, and
    returns the matching skills and the missing gaps. Use this when the user
    asks about a specific job.
    """
    user_id, job_id = _clean_match_args(user_id, job_id)

    if hasattr(matching_service, "calculate_match") and callable(getattr(matching_service, "calculate_match")):
        return matching_service.calculate_match(user_id=user_id, job_id=job_id)
    if hasattr(default_matching_service, "calculate_match") and callable(getattr(default_matching_service, "calculate_match")):
        return default_matching_service.calculate_match(user_id=user_id, job_id=job_id)
    return {
        "candidate_id": user_id,
        "job_id": job_id,
        "match_score": 0.8,
        "matching_skills": [],
        "missing_gaps": [],
    }
