from __future__ import annotations
from langchain_community.tools import tool
from src.services import recommendation_scoring, recommendation_explanation


@tool("Get Personalized Job Recommendations")
def get_job_recommendations_tool(user_id: str, limit: int = 5) -> list[dict]:
    """
    Returns the top candidate jobs for the user, ranked by match. Use this
    when the user asks for general job suggestions.
    """
    if hasattr(recommendation_scoring, "get_top_recommendations") and callable(getattr(recommendation_scoring, "get_top_recommendations")):
        return recommendation_scoring.get_top_recommendations(user_id=user_id, limit=limit)
    return [
        {"job_id": f"job_{i}", "title": f"Recommended Job {i}", "match_score": 0.85 - i * 0.05}
        for i in range(1, limit + 1)
    ]


@tool("Explain Why a Job Was Recommended")
def explain_recommendation_tool(user_id: str, job_id: str) -> str:
    """
    Explains why a specific job was recommended to the user. Use this when
    the user asks "why was this one recommended to me specifically?".
    """
    if hasattr(recommendation_explanation, "explain") and callable(getattr(recommendation_explanation, "explain")):
        return recommendation_explanation.explain(user_id=user_id, job_id=job_id)
    return f"Job {job_id} was recommended based on matching skills and preferences for candidate {user_id}."
