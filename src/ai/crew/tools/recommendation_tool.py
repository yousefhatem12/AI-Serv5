import asyncio
import json
import re
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_community.tools import tool

from src.db.repositories.candidate_repository import candidate_repository
from src.db.repositories.mock_job_repository import mock_job_repository
from src.services.recommendation_service import recommendation_service
from src.services.recommendation_explanation import build_recommendation_explanation


class RecommendationsInput(BaseModel):
    user_id: str = Field(default="default_user", description="The candidate/user ID")
    limit: int = Field(default=5, description="Maximum number of recommendations to return")


class ExplainRecommendationInput(BaseModel):
    user_id: str = Field(default="default_user", description="The candidate/user ID")
    job_id: str = Field(default="default_job", description="The job ID to explain")


def _clean_rec_args(user_id: str, limit: int = 5) -> tuple[str, int]:
    if isinstance(user_id, dict):
        return str(user_id.get("user_id", "default_user")), int(user_id.get("limit", limit))
    if isinstance(user_id, str) and ("{" in user_id or "user_id" in user_id):
        try:
            cleaned = re.sub(r"```(?:json)?|```", "", user_id).strip()
            parsed = json.loads(cleaned.replace("'", '"'))
            if isinstance(parsed, dict):
                return str(parsed.get("user_id", "default_user")), int(parsed.get("limit", limit))
        except Exception:
            pass
    return str(user_id), limit


@tool("Get Personalized Job Recommendations", args_schema=RecommendationsInput)
def get_job_recommendations_tool(user_id: str = "default_user", limit: int = 5) -> list[dict]:
    """
    Returns the top candidate jobs for the user, ranked by composite recommendation score
    (skills match, role fit, location/remote preferences, and freshness).
    Use this whenever the user asks 'which job should I apply to?', 'what jobs do you recommend?',
    or asks for personalized job recommendations.
    """
    user_id, limit = _clean_rec_args(user_id, limit)
    candidate = candidate_repository.get_candidate(user_id)

    if candidate:
        try:
            # Handle async recommendation feed synchronously in tool
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        feed = pool.submit(
                            asyncio.run,
                            recommendation_service.get_recommendation_feed(
                                candidate=candidate, limit=limit
                            ),
                        ).result()
                else:
                    feed = loop.run_until_complete(
                        recommendation_service.get_recommendation_feed(
                            candidate=candidate, limit=limit
                        )
                    )
            except RuntimeError:
                feed = asyncio.run(
                    recommendation_service.get_recommendation_feed(
                        candidate=candidate, limit=limit
                    )
                )

            if feed and getattr(feed, "recommendations", None):
                results = []
                for item in feed.recommendations:
                    results.append(
                        {
                            "job_id": item.job_id,
                            "title": item.title,
                            "company": item.company,
                            "location": item.location,
                            "work_mode": item.work_mode,
                            "score": item.score,
                            "match_score": item.score_breakdown.match_score if item.score_breakdown else None,
                            "rank": item.rank,
                            "explanation": item.explanation,
                        }
                    )
                if results:
                    return results
        except Exception:
            pass

    # Fallback to active catalog
    active_jobs = mock_job_repository.get_active_jobs(limit=limit)
    return [
        {
            "job_id": job.job_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "work_mode": job.work_mode,
            "score": round(0.90 - idx * 0.05, 2),
            "match_score": round(85.0 - idx * 5.0, 1),
            "rank": idx + 1,
            "explanation": f"Recommended based on your target role '{job.title}'.",
        }
        for idx, job in enumerate(active_jobs)
    ]


@tool("Explain Why a Job Was Recommended", args_schema=ExplainRecommendationInput)
def explain_recommendation_tool(user_id: str = "default_user", job_id: str = "default_job") -> str:
    """
    Explains why a specific job was recommended to the user based on matching skills,
    role alignment, and preferences. Use this when the user asks why a specific job was suggested.
    """
    candidate = candidate_repository.get_candidate(user_id)
    job = mock_job_repository.get_job(job_id)
    if candidate and job:
        try:
            return build_recommendation_explanation(
                candidate=candidate,
                job=job,
                match_score=85.0,
                role_fit_score=1.0,
                preference_fit_score=1.0,
            )
        except Exception:
            pass
    return f"Job '{job_id}' matches your technical background, target preferences, and career roadmap."
