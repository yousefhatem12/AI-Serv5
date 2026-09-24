from __future__ import annotations
from crewai import Agent
from src.core.llm import get_llm

from src.ai.crew.tools.cv_tool import get_cv_profile_tool
from src.ai.crew.tools.matching_tool import get_job_match_tool
from src.ai.crew.tools.recommendation_tool import (
    get_job_recommendations_tool,
    explain_recommendation_tool,
)
from src.ai.crew.tools.interview_tool import get_interview_prep_tool
from src.ai.crew.tools.roadmap_tool import get_roadmap_tool


mentor_agent = Agent(
    role="Mentor Agent",
    goal=(
        "Help the user make practical career decisions based on their real "
        "data (CV, jobs they've viewed, their roadmap) — without inventing "
        "any information not present in the available tools."
    ),
    backstory=(
        "You are an expert career mentor inside the SkillMatch platform. "
        "You don't give generic advice — every response of yours is based "
        "on real data fetched from the tools available to you."
    ),
    tools=[
        get_cv_profile_tool,
        get_job_match_tool,
        get_job_recommendations_tool,
        explain_recommendation_tool,
        get_interview_prep_tool,
        get_roadmap_tool,
    ],
    llm=get_llm(),
    memory=True,
    verbose=True,
    allow_delegation=False,
)

roadmap_agent = Agent(
    role="Roadmap Agent",
    goal="Build and update a practical, staged career plan based on real skill gaps.",
    backstory="A specialist in building actionable career-development plans, broken into stages and weekly goals.",
    tools=[get_cv_profile_tool, get_roadmap_tool],
    llm=get_llm(),
    memory=True,
    verbose=True,
    allow_delegation=False,
)

job_insights_agent = Agent(
    role="Job Insights Agent",
    goal="Explain how well-suited the user is for a specific job and whether they should apply now or wait.",
    backstory="A specialist in analyzing the fit between candidates and jobs with transparency and clear evidence.",
    tools=[get_job_match_tool, explain_recommendation_tool],
    llm=get_llm(),
    memory=True,
    verbose=True,
    allow_delegation=False,
)
