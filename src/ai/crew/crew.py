from __future__ import annotations
import inspect
from crewai import Crew, Process

from src.ai.crew.agents import mentor_agent, roadmap_agent, job_insights_agent
from src.ai.crew.tasks import (
    build_mentor_task,
    build_roadmap_task,
    build_job_insights_task,
)
from src.ai.suggested_prompts.agent_context import AgentType


def _classify_intent(user_message: str) -> AgentType:
    """
    A lightweight initial classification (rule-based or a fast model) to
    determine who should respond. Start with simple rule-based logic, and
    it can later be switched to a small classification model if needed.
    """
    lowered = user_message.lower()
    if any(k in lowered for k in ["roadmap", "plan", "milestone", "stage"]):
        return AgentType.ROADMAP
    if any(k in lowered for k in ["this job", "apply", "match", "fit"]):
        return AgentType.JOB_INSIGHTS
    return AgentType.MENTOR


async def run_mentor_crew_stream(user_message: str, context: dict):
    """
    Determines the appropriate Agent, runs its Task inside a separate Crew
    (so the streaming source is clear), and yields (token, agent_type)
    incrementally.
    """
    intent = _classify_intent(user_message)

    task_builders = {
        AgentType.MENTOR: build_mentor_task,
        AgentType.ROADMAP: build_roadmap_task,
        AgentType.JOB_INSIGHTS: build_job_insights_task,
    }
    task = task_builders[intent](user_message, context)

    crew = Crew(
        agents=[task.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    # CrewAI supports streaming either via kickoff_stream or kickoff fallback
    if hasattr(crew, "kickoff_stream") and callable(getattr(crew, "kickoff_stream")):
        stream = crew.kickoff_stream()
        if inspect.isasyncgen(stream):
            async for token in stream:
                yield str(token), intent
        else:
            for token in stream:
                yield str(token), intent
    else:
        import asyncio
        result = await asyncio.to_thread(crew.kickoff)
        output_str = str(result)
        chunk_size = 20
        for i in range(0, len(output_str), chunk_size):
            yield output_str[i : i + chunk_size], intent

    yield "", intent  # end-of-stream signal to guarantee agent_type is sent
