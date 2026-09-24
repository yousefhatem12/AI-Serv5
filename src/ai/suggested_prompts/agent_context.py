from __future__ import annotations
from enum import Enum
from pydantic import BaseModel


class AgentType(str, Enum):
    MENTOR = "Mentor Agent"
    ROADMAP = "Roadmap Agent"
    JOB_INSIGHTS = "Job Insights Agent"


class AgentContext(BaseModel):
    agent_type: AgentType
    last_output: str
    conversation_id: str
    user_id: str


AGENT_PROMPT_INSTRUCTIONS: dict[AgentType, str] = {
    AgentType.MENTOR: (
        "Focus the questions on: practical career advice, a specific next "
        "step, or a request for clarification on something mentioned in the "
        "Mentor's response."
    ),
    AgentType.ROADMAP: (
        "Focus the questions on: details of the upcoming milestone, "
        "suggested learning resources, or adjusting the roadmap's "
        "priorities."
    ),
    AgentType.JOB_INSIGHTS: (
        "Focus the questions on: details of the skill gap, the decision to "
        "apply now vs. wait, or other similar jobs."
    ),
}
