from __future__ import annotations
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.db.base import Base, get_db
from src.db.models.interview import InterviewSessionModel
from src.main import app
from src.schemas.interview import (
    MCQOption,
    MCQQuestion,
    EssayQuestion,
    ClientMCQQuestion,
    ClientEssayQuestion,
    PracticeQuestionGenerationRequest,
    PracticeSessionQuestionsResponse,
    AnswerItem,
    PracticeSubmissionRequest,
    MCQEvaluationItem,
    EssayEvaluationItem,
    OverallScore,
    PracticeEvaluationResponse,
    EssayGradingSchema,
    SummaryFeedbackSchema,
    PracticeQuestionSetGenerationResult,
)
from src.services.interview_service import (
    InterviewService,
    sanitize_question_for_client,
)
from src.ai.chains.interview_practice import PracticeInterviewChains


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def mock_practice_chains():
    chains = MagicMock(spec=PracticeInterviewChains)
    chains.generate_practice_questions = AsyncMock(return_value=[
        MCQQuestion(
            id="q_001",
            type="mcq",
            prompt="Which HTTP status code indicates a successful resource creation?",
            skill_tag="REST APIs",
            difficulty="easy",
            related_job_id="job_123",
            options=[
                MCQOption(id="a", text="200 OK"),
                MCQOption(id="b", text="201 Created"),
                MCQOption(id="c", text="204 No Content"),
                MCQOption(id="d", text="301 Moved Permanently"),
            ],
            correct_option_id="b",
            explanation="A 201 status indicates successful creation of a new resource.",
        ),
        EssayQuestion(
            id="q_002",
            type="essay",
            prompt="Explain optimistic vs pessimistic locking.",
            skill_tag="Database Design",
            difficulty="medium",
            related_job_id="job_123",
            reference_answer="Optimistic checks at commit; pessimistic locks upfront.",
            grading_criteria=[
                "Defines optimistic locking",
                "Defines pessimistic locking",
                "Provides a valid trade-off scenario",
            ],
        )
    ])
    chains.grade_essay = AsyncMock(return_value=EssayEvaluationItem(
        question_id="q_002",
        type="essay",
        score=85,
        points_possible=100,
        criteria_met=["Defines optimistic locking", "Defines pessimistic locking"],
        criteria_missed=["Provides a valid trade-off scenario"],
        feedback="Solid conceptual definitions. Add a concrete transaction scenario.",
    ))
    chains.generate_summary_feedback = AsyncMock(return_value="Strong database fundamentals with good REST API comprehension.")
    return chains


# ----------------------------------------------------------------------
# 1. Schemas Validation Tests
# ----------------------------------------------------------------------

def test_practice_schemas_validation():
    req = PracticeQuestionGenerationRequest(
        user_id="user_456",
        job_id="job_123",
        track="Backend Development",
        skill_gaps=["Database Design", "REST APIs"],
        total_questions=4,
        include_essay=True,
    )
    assert req.user_id == "user_456"
    assert req.track == "Backend Development"
    assert len(req.skill_gaps) == 2

    mcq = MCQQuestion(
        id="q_1",
        prompt="Sample MCQ",
        skill_tag="SQL",
        difficulty="hard",
        options=[MCQOption(id="a", text="Option A"), MCQOption(id="b", text="Option B")],
        correct_option_id="a",
    )
    assert mcq.difficulty == "hard"
    assert mcq.type == "mcq"

    essay = EssayQuestion(
        id="q_2",
        prompt="Sample Essay",
        skill_tag="System Design",
        reference_answer="Ideal answer.",
        grading_criteria=["Criterion 1", "Criterion 2"],
    )
    assert essay.type == "essay"
    assert len(essay.grading_criteria) == 2


# ----------------------------------------------------------------------
# 2. MCQ Deterministic Scoring Tests
# ----------------------------------------------------------------------

def test_mcq_scoring_correct_and_incorrect():
    service = InterviewService()

    # Correct submission (easy = 1 pt)
    res_correct = service.score_mcq_item(
        question_id="q_1",
        correct_option_id="b",
        submitted_option_id="b",
        difficulty="easy",
        explanation="201 is created.",
    )
    assert res_correct.is_correct is True
    assert res_correct.points_earned == 1
    assert res_correct.points_possible == 1
    assert "Correct!" in res_correct.feedback
    assert "201 is created" in res_correct.feedback

    # Incorrect submission (medium = 2 pts)
    res_incorrect = service.score_mcq_item(
        question_id="q_2",
        correct_option_id="b",
        submitted_option_id="a",
        difficulty="medium",
        explanation="201 is created.",
    )
    assert res_incorrect.is_correct is False
    assert res_incorrect.points_earned == 0
    assert res_incorrect.points_possible == 2
    assert "Incorrect" in res_incorrect.feedback
    assert "correct answer is 'b'" in res_incorrect.feedback

    # Hard difficulty points
    res_hard = service.score_mcq_item(
        question_id="q_3",
        correct_option_id="c",
        submitted_option_id="c",
        difficulty="hard",
    )
    assert res_hard.points_earned == 3
    assert res_hard.points_possible == 3

    # Missing submission
    res_missing = service.score_mcq_item(
        question_id="q_4",
        correct_option_id="d",
        submitted_option_id=None,
        difficulty="easy",
    )
    assert res_missing.is_correct is False
    assert res_missing.points_earned == 0
    assert "No answer was submitted" in res_missing.feedback

    # Case insensitivity ('A' == 'a')
    res_case = service.score_mcq_item(
        question_id="q_5",
        correct_option_id="a",
        submitted_option_id="A",
        difficulty="easy",
    )
    assert res_case.is_correct is True



# 3. Essay Scoring & Fallback Tests


@pytest.mark.asyncio
async def test_essay_grading_precheck_empty_answer():
    chains = PracticeInterviewChains()

    # Empty or whitespace answer should short-circuit and not call LLM
    res = await chains.grade_essay(
        question_id="q_essay_1",
        prompt="Explain microservices architecture.",
        skill_tag="Architecture",
        reference_answer="Reference...",
        grading_criteria=["Criterion 1"],
        submitted_answer="   ",
    )
    assert res.score == 0
    assert res.points_possible == 100
    assert res.criteria_met == []
    assert res.criteria_missed == ["Criterion 1"]
    assert "No substantive answer" in res.feedback


@pytest.mark.asyncio
async def test_essay_grading_structured_success():
    mock_llm = MagicMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke.return_value = EssayGradingSchema(
        score=92,
        criteria_met=["Criterion A", "Criterion B"],
        criteria_missed=[],
        feedback="Excellent and comprehensive response.",
    )
    mock_llm.with_structured_output.return_value = mock_structured

    chains = PracticeInterviewChains(llm=mock_llm)
    res = await chains.grade_essay(
        question_id="q_essay_2",
        prompt="Explain indexing.",
        skill_tag="Databases",
        reference_answer="B-Tree indexes speed up lookups...",
        grading_criteria=["Criterion A", "Criterion B"],
        submitted_answer="Indexes organize data in tree structures for logarithmic lookups.",
    )
    assert res.score == 92
    assert len(res.criteria_met) == 2
    assert len(res.criteria_missed) == 0
    assert res.feedback == "Excellent and comprehensive response."


@pytest.mark.asyncio
async def test_essay_grading_timeout_and_exception_fallback():
    mock_llm = MagicMock()
    mock_structured = AsyncMock(side_effect=asyncio.TimeoutError())
    mock_llm.with_structured_output.return_value = mock_structured

    chains = PracticeInterviewChains(llm=mock_llm)
    res = await chains.grade_essay(
        question_id="q_essay_3",
        prompt="Explain CAP theorem.",
        skill_tag="Distributed Systems",
        reference_answer="Consistency, Availability, Partition Tolerance...",
        grading_criteria=["Mentions C, A, P"],
        submitted_answer="CAP theorem states you can only pick two guarantees.",
        timeout_seconds=0.01,
    )
    assert res.score is None
    assert res.points_possible == 100
    assert "Grading unavailable" in res.feedback



# 4. Question Masking / Sanitization Tests


def test_question_sanitization_for_client():
    mcq = MCQQuestion(
        id="q_mcq",
        prompt="What is REST?",
        skill_tag="APIs",
        options=[MCQOption(id="a", text="A"), MCQOption(id="b", text="B")],
        correct_option_id="a",
        explanation="Secret explanation",
    )
    sanitized_mcq = sanitize_question_for_client(mcq)
    assert "correct_option_id" not in sanitized_mcq
    assert "explanation" not in sanitized_mcq
    assert sanitized_mcq["id"] == "q_mcq"

    essay = EssayQuestion(
        id="q_essay",
        prompt="Design a cache.",
        skill_tag="System Design",
        reference_answer="Secret reference answer",
        grading_criteria=["Secret criterion 1", "Secret criterion 2"],
    )
    sanitized_essay = sanitize_question_for_client(essay)
    assert "reference_answer" not in sanitized_essay
    assert "grading_criteria" not in sanitized_essay
    assert sanitized_essay["id"] == "q_essay"



# 5. Service Practice Session & Evaluation Flow Tests


@pytest.mark.asyncio
async def test_generate_practice_session_and_evaluate(in_memory_db, mock_practice_chains):
    service = InterviewService(practice_chains=mock_practice_chains)

    # 1. Generate session
    gen_req = PracticeQuestionGenerationRequest(
        user_id="user_100",
        job_id="job_200",
        track="Backend Development",
        skill_gaps=["REST APIs", "Database Design"],
        total_questions=2,
        include_essay=True,
    )
    session_data = await service.generate_practice_session(gen_req, db=in_memory_db, mask_answers=True)

    session_id = session_data["session_id"]
    assert session_id.startswith("sess_")
    assert len(session_data["questions"]) == 2

    # Verify answers/rubric are masked in returned questions
    q0 = session_data["questions"][0]
    q1 = session_data["questions"][1]
    assert "correct_option_id" not in q0
    assert "reference_answer" not in q1

    # Verify DB persistence
    stored = service.get_practice_session(session_id, db=in_memory_db)
    assert stored is not None
    assert stored.user_id == "user_100"
    assert stored.track == "Backend Development"
    assert len(stored.questions) == 2
    # In DB, full questions contain secrets
    assert stored.questions[0].get("correct_option_id") == "b"

    # 2. Submit candidate answers
    sub_req = PracticeSubmissionRequest(
        session_id=session_id,
        user_id="user_100",
        job_id="job_200",
        answers=[
            AnswerItem(
                question_id="q_001",
                type="mcq",
                submitted_option_id="b",  # correct
            ),
            AnswerItem(
                question_id="q_002",
                type="essay",
                submitted_answer="Optimistic locking checks version at commit; pessimistic locks rows.",
            )
        ]
    )

    eval_result = await service.evaluate_practice_submission(sub_req, db=in_memory_db)
    assert eval_result.session_id == session_id
    assert len(eval_result.per_question) == 2

    # MCQ evaluation (easy = 1 pt)
    mcq_eval = eval_result.per_question[0]
    assert isinstance(mcq_eval, MCQEvaluationItem)
    assert mcq_eval.is_correct is True
    assert mcq_eval.points_earned == 1

    # Essay evaluation (85 / 100)
    essay_eval = eval_result.per_question[1]
    assert isinstance(essay_eval, EssayEvaluationItem)
    assert essay_eval.score == 85

    # Overall score: (1 + 85) / (1 + 100) = 86 / 101 = 85.1%
    assert eval_result.overall_score.raw_points == 86.0
    assert eval_result.overall_score.max_points == 101.0
    assert eval_result.overall_score.percentage == pytest.approx(85.1, 0.1)

    # Verify DB was updated with submission and evaluation
    updated_session = service.get_practice_session(session_id, db=in_memory_db)
    assert updated_session.answers is not None
    assert updated_session.evaluation is not None
    assert updated_session.evaluation["overall_score"]["percentage"] == pytest.approx(85.1, 0.1)


# ----------------------------------------------------------------------
# 6. Fallback Question Generator (No LLM)
# ----------------------------------------------------------------------

def test_practice_chains_fallback_questions():
    chains = PracticeInterviewChains()
    fallback_qs = chains._generate_fallback_questions(
        track="DevOps",
        skill_gaps=["Kubernetes", "CI/CD"],
        job_id="job_devops",
        total_questions=4,
        include_essay=True,
    )
    assert len(fallback_qs) == 4
    mcq_count = sum(1 for q in fallback_qs if q.type == "mcq")
    essay_count = sum(1 for q in fallback_qs if q.type == "essay")
    assert mcq_count >= 1
    assert essay_count >= 1
    assert fallback_qs[0].skill_tag in ["Kubernetes", "CI/CD"]



# 7. FastAPI Endpoint Integration Tests


def test_api_practice_coach_endpoints(in_memory_db, mock_practice_chains):
    from src.services.interview_service import interview_service
    interview_service.practice_chains = mock_practice_chains

    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        # 1. POST /api/v1/interview/prep/generate
        gen_payload = {
            "user_id": "user_api_1",
            "job_id": "job_api_1",
            "track": "Data Science",
            "skill_gaps": ["Pandas", "Model Evaluation"],
            "total_questions": 2,
            "include_essay": True,
        }
        res_gen = client.post("/api/v1/interview/prep/generate", json=gen_payload)
        assert res_gen.status_code == 200
        gen_data = res_gen.json()
        assert "session_id" in gen_data
        session_id = gen_data["session_id"]
        assert len(gen_data["questions"]) == 2
        # Verify secrets masked
        assert "correct_option_id" not in gen_data["questions"][0]

        # 2. POST /api/v1/interview/prep/submit
        submit_payload = {
            "session_id": session_id,
            "user_id": "user_api_1",
            "job_id": "job_api_1",
            "answers": [
                {
                    "question_id": "q_001",
                    "type": "mcq",
                    "submitted_option_id": "b"
                },
                {
                    "question_id": "q_002",
                    "type": "essay",
                    "submitted_answer": "Optimistic locking checks at commit time."
                }
            ]
        }
        res_submit = client.post("/api/v1/interview/prep/submit", json=submit_payload)
        assert res_submit.status_code == 200
        eval_data = res_submit.json()
        assert eval_data["session_id"] == session_id
        assert len(eval_data["per_question"]) == 2
        assert "overall_score" in eval_data

        # 3. GET /api/v1/interview/prep/sessions/{session_id}
        res_get = client.get(f"/api/v1/interview/prep/sessions/{session_id}")
        assert res_get.status_code == 200
        session_detail = res_get.json()
        assert session_detail["session_id"] == session_id
        assert session_detail["user_id"] == "user_api_1"
        assert session_detail["evaluation"] is not None

        # 4. GET invalid session -> 404
        res_404 = client.get("/api/v1/interview/prep/sessions/sess_nonexistent")
        assert res_404.status_code == 404
    finally:
        app.dependency_overrides.clear()
