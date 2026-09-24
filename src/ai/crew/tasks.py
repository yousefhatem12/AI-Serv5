from __future__ import annotations
from crewai import Task
from src.ai.crew.agents import mentor_agent, roadmap_agent, job_insights_agent


def build_mentor_task(user_message: str, context: dict) -> Task:
    return Task(
        description=(
            f"User message: {user_message}\n\n"
            f"Available context: {context}\n\n"
            "Answer using only the available tools. If you need data that "
            "isn't in the context, use the appropriate tool."
        ),
        expected_output="A direct, useful response to the user based on real data.",
        agent=mentor_agent,
    )


def build_roadmap_task(user_message: str, context: dict) -> Task:
    return Task(
        description=f"User message: {user_message}\n\nAvailable context: {context}",
        expected_output="A plan or update to the roadmap based on real gaps.",
        agent=roadmap_agent,
    )


def build_job_insights_task(user_message: str, context: dict) -> Task:
    return Task(
        description=f"User message: {user_message}\n\nAvailable context: {context}",
        expected_output="A clear compatibility analysis with the job mentioned.",
        agent=job_insights_agent,
    )
