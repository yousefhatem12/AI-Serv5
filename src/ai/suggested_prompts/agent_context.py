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
        "Focus the questions on: Goal Clarification (target role, timeframe, concrete milestones), "
        "Application Debrief (extracting lessons from past interviews/rejections), "
        "or identifying missing evidence and practical next steps."
    ),
    AgentType.ROADMAP: (
        "Focus the questions on: Weekly Action Planning (practice tasks, portfolio projects, CV updates), "
        "Roadmap Adjustment (reprioritizing stages after new skills or completed projects), "
        "or clarifying milestone deadlines."
    ),
    AgentType.JOB_INSIGHTS: (
        "Focus the questions on: Job-Specific Advice (analyzing specific job requirements vs profile), "
        "Interview Readiness (high-priority topics to practice before interviews), "
        "or evaluating whether to apply now vs close specific skill gaps."
    ),
}
