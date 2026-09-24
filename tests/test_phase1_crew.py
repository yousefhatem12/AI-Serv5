from __future__ import annotations
import src.ai
import pytest
from src.db.base import init_db
from src.models.mentor_conversation import MentorConversation
from src.models.mentor_message import MentorMessage
from src.ai.crew.agents import mentor_agent, roadmap_agent, job_insights_agent
from src.ai.crew.tasks import build_mentor_task, build_roadmap_task, build_job_insights_task
from src.ai.crew.crew import _classify_intent, run_mentor_crew_stream
from src.ai.suggested_prompts.agent_context import AgentType
from src.ai.crew.tools.cv_tool import get_cv_profile_tool
from src.ai.crew.tools.matching_tool import get_job_match_tool
from src.ai.crew.tools.recommendation_tool import get_job_recommendations_tool, explain_recommendation_tool
from src.ai.crew.tools.interview_tool import get_interview_prep_tool
from src.ai.crew.tools.roadmap_tool import get_roadmap_tool
from src.ai.memory.chat_history import save_turn, get_recent_messages
from src.ai.memory.context_builder import build_mentor_context


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def test_tools_import_and_execution():
    cv_res = get_cv_profile_tool.func(user_id="cand_001")
    assert cv_res is not None

    match_res = get_job_match_tool.func(user_id="cand_001", job_id="job_001")
    assert match_res is not None

    rec_res = get_job_recommendations_tool.func(user_id="cand_001", limit=2)
    assert rec_res is not None

    exp_res = explain_recommendation_tool.func(user_id="cand_001", job_id="job_001")
    assert exp_res is not None

    prep_res = get_interview_prep_tool.func(user_id="cand_001", job_id="job_001")
    assert prep_res is not None

    roadmap_res = get_roadmap_tool.func(user_id="cand_001")
    assert roadmap_res is not None


def test_agents_configuration():
    assert mentor_agent.allow_delegation is False
    assert roadmap_agent.allow_delegation is False
    assert job_insights_agent.allow_delegation is False

    assert len(mentor_agent.tools) == 6
    assert len(roadmap_agent.tools) == 2
    assert len(job_insights_agent.tools) == 3


def test_intent_classification():
    # Goal Clarification & General Mentoring -> MENTOR
    assert _classify_intent("I want a backend internship, what should my goal and timeline look like?") == AgentType.MENTOR
    assert _classify_intent("How can I improve my resume?") == AgentType.MENTOR

    # Weekly Action Planning & Roadmap Adjustment -> ROADMAP
    assert _classify_intent("Help me build a roadmap for my career") == AgentType.ROADMAP
    assert _classify_intent("Can you make a weekly action plan for this milestone?") == AgentType.ROADMAP
    assert _classify_intent("I finished a project, how should I adjust roadmap priorities?") == AgentType.ROADMAP

    # Job-Specific Advice, Interview Readiness & Application Debrief -> JOB_INSIGHTS
    assert _classify_intent("Should I apply for this job?") == AgentType.JOB_INSIGHTS
    assert _classify_intent("How do my skills match this job requirements?") == AgentType.JOB_INSIGHTS
    assert _classify_intent("Which topics should I practice for interview readiness?") == AgentType.JOB_INSIGHTS
    assert _classify_intent("I was rejected after the technical interview, let's debrief") == AgentType.JOB_INSIGHTS


def test_task_builders():
    task_m = build_mentor_task("I want a backend internship", {"candidate_profile": {}})
    assert task_m.agent == mentor_agent
    assert "Goal Clarification" in task_m.description
    assert "Truthfulness & Boundaries" in task_m.description

    task_r = build_roadmap_task("Give me a weekly plan", {"candidate_profile": {}})
    assert task_r.agent == roadmap_agent
    assert "Weekly Action Planning" in task_r.description
    assert "Roadmap Adjustment" in task_r.description

    task_j = build_job_insights_task("Match report for this job", {"candidate_profile": {}})
    assert task_j.agent == job_insights_agent
    assert "Job-Specific Advice" in task_j.description
    assert "Interview Readiness" in task_j.description


@pytest.mark.asyncio
async def test_memory_persistence():
    import uuid
    conv_id = f"test_conv_{uuid.uuid4().hex}"
    await save_turn(conv_id, "Hello Mentor", "Hello User")
    await save_turn(conv_id, "What is my next step?", "Follow your roadmap")

    messages = await get_recent_messages(conv_id, limit=10)
    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello Mentor"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello User"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "What is my next step?"
    assert messages[3]["role"] == "assistant"
    assert messages[3]["content"] == "Follow your roadmap"

    ctx = await build_mentor_context(
        user_id="cand_001",
        conversation_id=conv_id,
        job_id="job_001",
        target_role="Backend Engineer",
        career_preferences={"remote": True},
        saved_jobs=["job_002"],
        applied_jobs=[{"job_id": "job_003", "status": "applied"}],
        application_statuses=[{"job_id": "job_004", "status": "rejected", "stage": "technical_interview"}],
        user_notes=["Focus on async Python and PostgreSQL"],
        current_milestones=["Master FastAPI"],
    )
    # Check all allowed context elements
    assert "candidate_profile" in ctx
    assert "cv_summary" in ctx
    assert ctx["target_role"] == "Backend Engineer"
    assert ctx["career_preferences"] == {"remote": True}
    assert ctx["selected_job_id"] == "job_001"
    assert "job_002" in ctx["saved_jobs"]
    assert len(ctx["applied_jobs"]) == 1
    assert len(ctx["application_statuses"]) == 1
    assert "Focus on async Python and PostgreSQL" in ctx["user_notes"]
    assert "Master FastAPI" in ctx["completed_milestones"]
    assert "recent_messages" in ctx
