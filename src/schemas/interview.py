from __future__ import annotations
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

class QuestionGenerationRequest(BaseModel):
    job_id: str
    target_role: str
    candidate_id: str
    focus_skills: List[str] = Field(
        default=[],
        description="List of skill_ids to target (e.g. ['skill_sql', 'skill_statistics'])"
    )
    job_summary: Optional[str] = Field(
        default=None,
        description="Optional detailed job requirements summary."
    )
    include_essay: bool = Field(
        default=True,
        description="Whether to include architectural/open-ended essay questions."
    )

class AnswerSubmission(BaseModel):
    question_id: str
    question_text: str
    question_type: Optional[str] = Field(
        default="technical",
        description="Type of question: technical, behavioral, system_design, or essay"
    )
    skill_id: Optional[str] = None
    user_answer: str

    # --- Output Schemas ---

class InterviewQuestion(BaseModel):
    question_id:str
    skill_id: Optional[str]= None
    type:str = Field(description="'technical', 'behavioral', or 'system_design'")
    question:str
    context_or_scenario: Optional[str] = None
    key_points_to_cover: List[str] = Field(description="Internal rubric for evaluation")
    security_focus_areas: List[str] = Field(
        default=[],
        description="Specific security concerns (e.g. SQLi, RBAC, Data Encryption) to address."
    )

class QuestionSetResponse(BaseModel):
    job_id: str
    target_role: str
    questions: List[InterviewQuestion]

# Security-specific evaluation breakdown
class SecurityAssessment(BaseModel):
    has_security_vulnerabilities: bool = Field(
        description="True if candidate's answer introduces or overlooks critical security risks."
    )
    identified_risks: List[str] = Field(
        default=[],
        description="List of security risks present in the user's response."
    )
    security_score: int = Field(
        description="Score from 1 to 10 evaluating security posture and awareness."
    )
    mitigation_suggestions: List[str] = Field(
        default=[],
        description="Actions to patch identified vulnerabilities or enhance security."
    )

class AnswerEvaluationResponse(BaseModel):
    question_id: str
    score: int = Field(description="score from 1 to 10")
    strengths: List[str]
    improvements: List[str]
    ideal_answer_outline: str
    security_assessment: Optional[SecurityAssessment] = Field(
        default=None,
        description="Detailed security review for essay, coding, or system design answers."
    )
    recommended_action: Optional[str] = None


# ======================================================================
# Practice Coach (MCQ + Essay + Scoring) Schemas (§5 of Requirements)
# ======================================================================

class MCQOption(BaseModel):
    id: str = Field(description="Option identifier, e.g. 'a', 'b', 'c', 'd'")
    text: str = Field(description="Option text")


class MCQQuestion(BaseModel):
    id: str
    type: str = Field(default="mcq", description="Always 'mcq'")
    prompt: str
    skill_tag: str = Field(description="Skill gap or competency tested")
    difficulty: str = Field(default="medium", description="'easy', 'medium', or 'hard'")
    related_job_id: Optional[str] = None
    options: List[MCQOption]
    correct_option_id: Optional[str] = Field(
        default=None,
        description="Correct option identifier. Hidden from candidate until scored."
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Brief explanation of why the correct option is correct."
    )


class EssayQuestion(BaseModel):
    id: str
    type: str = Field(default="essay", description="Always 'essay'")
    prompt: str
    skill_tag: str = Field(description="Skill gap or competency tested")
    difficulty: str = Field(default="medium", description="'easy', 'medium', or 'hard'")
    related_job_id: Optional[str] = None
    reference_answer: Optional[str] = Field(
        default=None,
        description="Ideal reference answer. Hidden from candidate until scored."
    )
    grading_criteria: Optional[List[str]] = Field(
        default=[],
        description="Key criteria required for full points. Hidden from candidate until scored."
    )


class ClientMCQQuestion(BaseModel):
    id: str
    type: str = Field(default="mcq", description="Always 'mcq'")
    prompt: str
    skill_tag: str = Field(description="Skill gap or competency tested")
    difficulty: str = Field(default="medium", description="'easy', 'medium', or 'hard'")
    related_job_id: Optional[str] = None
    options: List[MCQOption]


class ClientEssayQuestion(BaseModel):
    id: str
    type: str = Field(default="essay", description="Always 'essay'")
    prompt: str
    skill_tag: str = Field(description="Skill gap or competency tested")
    difficulty: str = Field(default="medium", description="'easy', 'medium', or 'hard'")
    related_job_id: Optional[str] = None


class PracticeQuestionGenerationRequest(BaseModel):
    user_id: str = Field(description="Candidate identifier")
    job_id: str = Field(description="Target job identifier")
    track: str = Field(description="Career track/field, e.g., 'Backend Development'")
    skill_gaps: List[str] = Field(
        default=[],
        description="Target skill gaps to generate personalized questions for"
    )
    total_questions: Optional[int] = Field(
        default=4,
        ge=2,
        le=10,
        description="Total number of practice questions to generate"
    )
    include_essay: bool = Field(
        default=True,
        description="Whether to include open-ended essay questions alongside MCQs"
    )


class PracticeSessionQuestionsResponse(BaseModel):
    session_id: str
    user_id: str
    job_id: str
    track: str
    skill_gaps: List[str]
    questions: List[Union[ClientMCQQuestion, ClientEssayQuestion]]



class AnswerItem(BaseModel):
    question_id: str
    type: str = Field(description="'mcq' or 'essay'")
    correct_option_id: Optional[str] = Field(
        default=None,
        description="MCQ true answer (can be pre-supplied or hydrated from session)"
    )
    submitted_option_id: Optional[str] = Field(
        default=None,
        description="Candidate's selected option id for MCQ (e.g. 'a')"
    )
    reference_answer: Optional[str] = Field(
        default=None,
        description="Essay reference answer (can be pre-supplied or hydrated from session)"
    )
    grading_criteria: Optional[List[str]] = Field(
        default=None,
        description="Essay grading criteria list"
    )
    submitted_answer: Optional[str] = Field(
        default=None,
        description="Candidate's open-ended written answer for Essay"
    )


class PracticeSubmissionRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    job_id: Optional[str] = None
    answers: List[AnswerItem]


class MCQEvaluationItem(BaseModel):
    question_id: str
    type: str = Field(default="mcq")
    is_correct: bool
    points_earned: int
    points_possible: int
    feedback: str


class EssayEvaluationItem(BaseModel):
    question_id: str
    type: str = Field(default="essay")
    score: Optional[int] = Field(default=None, ge=0, le=100)
    points_possible: int = 100
    criteria_met: List[str] = []
    criteria_missed: List[str] = []
    feedback: str


class OverallScore(BaseModel):
    raw_points: float
    max_points: float
    percentage: float


class PracticeEvaluationResponse(BaseModel):
    session_id: str
    per_question: List[Union[MCQEvaluationItem, EssayEvaluationItem]]
    overall_score: OverallScore
    summary_feedback: str


class EssayGradingSchema(BaseModel):
    score: int = Field(ge=0, le=100, description="Numeric grade from 0 to 100")
    criteria_met: List[str] = Field(default=[], description="List of criteria satisfied by the candidate's answer")
    criteria_missed: List[str] = Field(default=[], description="List of criteria missing or inadequate in the candidate's answer")
    feedback: str = Field(description="Constructive role-relevant feedback based only on reference answer and rubric")


class PracticeQuestionSetGenerationResult(BaseModel):
    mcq_questions: List[MCQQuestion] = Field(default_factory=list, description="List of generated MCQ questions")
    essay_questions: List[EssayQuestion] = Field(default_factory=list, description="List of generated Essay questions")


class SummaryFeedbackSchema(BaseModel):
    summary_feedback: str = Field(description="Summary paragraph of performance, strengths, and top 1-2 areas to improve.")


class PracticeSessionDetailResponse(BaseModel):
    session_id: str
    user_id: str
    job_id: str
    track: Optional[str] = None
    skill_gaps: List[str] = []
    questions: List[Dict[str, Any]]
    answers: Optional[List[Dict[str, Any]]] = None
    evaluation: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


