from __future__ import annotations
import json
import re
from pydantic import BaseModel, Field
from langchain_community.tools import tool

from src.services.application_strategy_service import application_strategy_service


class ApplicationStrategyInput(BaseModel):
    user_id: str = Field(default="default_user", description="The candidate/user ID")
    job_id: str = Field(
        default="default_job",
        description="The target job ID to evaluate. If the user does not specify a specific job ID, leave as default_job to evaluate their primary active role.",
    )


def _clean_strategy_args(user_id: str, job_id: str = "default_job") -> tuple[str, str]:
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


@tool("Get Application Strategy Guidance", args_schema=ApplicationStrategyInput)
def get_application_strategy_tool(user_id: str = "default_user", job_id: str = "default_job") -> dict:
    """
    Evaluates whether the candidate should 'apply now', 'apply while improving gaps',
    or 'prioritize another role first'. Use this tool whenever the user asks which job
    they can apply for, whether they should apply now vs wait, if they are qualified
    for a specific job, or when they request a structured application strategy and action plan.
    """
    user_id, job_id = _clean_strategy_args(user_id, job_id)
    strategy = application_strategy_service.generate_strategy(user_id=user_id, job_id=job_id)
    if hasattr(strategy, "model_dump"):
        return strategy.model_dump()
    if hasattr(strategy, "dict"):
        return strategy.dict()
    return {"candidate_id": user_id, "job_id": job_id, "decision": "apply_now", "disclaimer": "Advice only."}
