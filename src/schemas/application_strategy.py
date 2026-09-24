from __future__ import annotations
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class StrategyDecision(str, Enum):
    APPLY_NOW = "apply_now"
    APPLY_WHILE_IMPROVING = "apply_while_improving"
    PRIORITIZE_ANOTHER_ROLE = "prioritize_another_role"


class GapSeverity(str, Enum):
    BLOCKER = "blocker"
    MODERATE = "moderate"
    MINOR = "minor"


class GapItem(BaseModel):
    skill: str = Field(description="Skill or competency name")
    severity: GapSeverity = Field(default=GapSeverity.MODERATE, description="Severity of the gap")
    rationale: str = Field(default="", description="Why this gap impacts the target job")


class StrategyActionItem(BaseModel):
    task: str = Field(description="Concrete action or study task")
    category: str = Field(default="practice_task", description="Action category (e.g., practice_task, portfolio, cv_update, application)")
    timeframe: str = Field(default="Week 1", description="Suggested timeframe to complete the task")
    impact: str = Field(default="High", description="Impact on qualification or match (High/Medium/Low)")


class AlternativeRole(BaseModel):
    role_title: str = Field(description="Recommended alternative or stepping-stone role")
    match_score: float = Field(default=0.8, description="Estimated match percentage (0.0 - 1.0)")
    rationale: str = Field(description="Why this role is an immediate viable stepping stone")
    transition_effort: str = Field(default="Low", description="Estimated effort to transition (Low/Medium/High)")


class ApplicationStrategyRequest(BaseModel):
    user_id: str = Field(description="Candidate / User ID")
    job_id: str = Field(description="Target Job ID")
    target_role: Optional[str] = Field(default=None, description="Optional target career track/role")
    user_notes: Optional[str] = Field(default=None, description="Optional user goals or context notes")


class ApplicationStrategyResponse(BaseModel):
    candidate_id: str
    job_id: str
    job_title: Optional[str] = None
    decision: StrategyDecision
    match_score: float = Field(ge=0.0, le=1.0)
    summary_reasoning: str
    strengths: List[str] = Field(default_factory=list)
    blocker_gaps: List[GapItem] = Field(default_factory=list)
    manageable_gaps: List[GapItem] = Field(default_factory=list)
    action_plan: List[StrategyActionItem] = Field(default_factory=list)
    alternative_roles: List[AlternativeRole] = Field(default_factory=list)
    disclaimer: str = Field(
        default="This strategy is professional career advice based on available profile and job requirements data, not a guarantee of hiring outcomes."
    )
