from __future__ import annotations
from src.ai.memory.chat_history import get_recent_messages
from src.ai.crew.tools.cv_tool import get_cv_profile_tool
from src.ai.crew.tools.roadmap_tool import get_roadmap_tool
from src.ai.crew.tools.matching_tool import get_job_match_tool


async def build_mentor_context(
    user_id: str,
    conversation_id: str,
    job_id: str | None = None,
    target_role: str | None = None,
    career_preferences: dict | None = None,
    saved_jobs: list | None = None,
    applied_jobs: list | None = None,
    application_statuses: list | None = None,
    match_reports: list | None = None,
    user_notes: list | None = None,
    current_milestones: list | None = None,
) -> dict:
    """
    Assembles the structured context the AI Mentor is allowed to use:
    1. Candidate profile and verified CV extraction
    2. Target role and career preferences
    3. Selected, saved and applied jobs
    4. Match reports and prioritized skill gaps
    5. Current roadmap, completed milestones and user notes
    6. Application statuses that the user has recorded
    7. Recent conversation history
    """
    recent_messages = await get_recent_messages(conversation_id)
    
    # 1. Candidate profile and verified CV extraction
    if hasattr(get_cv_profile_tool, "func"):
        cv_profile = get_cv_profile_tool.func(user_id=user_id)
    else:
        cv_profile = get_cv_profile_tool.invoke({"user_id": user_id})

    # 2. Roadmap and milestones
    if hasattr(get_roadmap_tool, "func"):
        roadmap = get_roadmap_tool.func(user_id=user_id)
    else:
        roadmap = get_roadmap_tool.invoke({"user_id": user_id})

    # 3. Match report and skill gaps (if job_id provided or available)
    match_data = None
    if job_id:
        if hasattr(get_job_match_tool, "func"):
            match_data = get_job_match_tool.func(user_id=user_id, job_id=job_id)
        else:
            match_data = get_job_match_tool.invoke({"user_id": user_id, "job_id": job_id})

    return {
        "candidate_profile": cv_profile,
        "cv_summary": cv_profile,
        "target_role": target_role or cv_profile.get("target_role") or "Backend Engineer",
        "career_preferences": career_preferences or cv_profile.get("career_preferences") or {},
        "selected_job_id": job_id,
        "saved_jobs": saved_jobs or [],
        "applied_jobs": applied_jobs or [],
        "match_reports": match_reports or ([match_data] if match_data else []),
        "prioritized_skill_gaps": match_data.get("missing_gaps", []) if isinstance(match_data, dict) else [],
        "current_roadmap": roadmap,
        "completed_milestones": current_milestones or roadmap.get("completed_milestones", []),
        "user_notes": user_notes or [],
        "application_statuses": application_statuses or [],
        "recent_messages": recent_messages,
    }
