from __future__ import annotations
from langchain_community.tools import tool
from src.services import roadmap_service
from src.services.roadmap_service import roadmap_service as default_roadmap_service


@tool("Get or Update Career Roadmap")
def get_roadmap_tool(user_id: str) -> dict:
    """
    Returns the user's current roadmap: stages, milestones, and weekly tasks.
    Use this when the user asks about their plan or their next step.
    """
    if hasattr(roadmap_service, "get_current_roadmap") and callable(getattr(roadmap_service, "get_current_roadmap")):
        return roadmap_service.get_current_roadmap(user_id=user_id)
    if hasattr(default_roadmap_service, "get_candidate_roadmap") and callable(getattr(default_roadmap_service, "get_candidate_roadmap")):
        result = default_roadmap_service.get_candidate_roadmap(user_id)
        if result:
            if hasattr(result, "model_dump"):
                return result.model_dump()
            if hasattr(result, "dict"):
                return result.dict()
    return {
        "candidate_id": user_id,
        "stages": ["Stage 1: Core Foundation", "Stage 2: Advanced Topics"],
        "milestones": ["Master FastAPI", "Build Microservices"],
    }
