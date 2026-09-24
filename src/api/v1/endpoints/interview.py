from __future__ import annotations
"""FastAPI endpoint for the Interview Preparation Coach feature."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.base import get_db
from src.schemas.interview import (
    QuestionGenerationRequest,
    QuestionSetResponse,
    AnswerSubmission,
    AnswerEvaluationResponse,
    PracticeQuestionGenerationRequest,
    PracticeSessionQuestionsResponse,
    PracticeSubmissionRequest,
    PracticeEvaluationResponse,
    PracticeSessionDetailResponse,
)
from src.services.interview_service import interview_service

router = APIRouter(prefix="/interview", tags=["Interview Preparation Coach"])


@router.post("/generate", response_model=QuestionSetResponse, status_code=status.HTTP_200_OK)
async def generate_interview_questions(payload: QuestionGenerationRequest):
    return await interview_service.create_prep_session(payload)


@router.post("/evaluate", response_model=AnswerEvaluationResponse, status_code=status.HTTP_200_OK)
async def evaluate_interview_answer(payload: AnswerSubmission):
    return await interview_service.evaluate_submission(payload)


# ----------------------------------------------------------------------
# Practice Coach Endpoints (§7 of Requirements)
# ----------------------------------------------------------------------

@router.post(
    "/prep/generate",
    response_model=PracticeSessionQuestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate practice MCQ and essay questions driven by track and skill gaps",
)
async def generate_practice_questions(
    payload: PracticeQuestionGenerationRequest,
    db: Session = Depends(get_db),
):
    return await interview_service.generate_practice_session(payload, db=db, mask_answers=True)


@router.post(
    "/prep/submit",
    response_model=PracticeEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit practice answers and receive structured feedback and numeric scoring",
)
async def submit_practice_answers(
    payload: PracticeSubmissionRequest,
    db: Session = Depends(get_db),
):
    return await interview_service.evaluate_practice_submission(payload, db=db)


@router.get(
    "/prep/sessions/{session_id}",
    response_model=PracticeSessionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve full past practice session details, submitted answers, and evaluation",
)
async def get_practice_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    session = interview_service.get_practice_session(session_id=session_id, db=db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Practice session '{session_id}' not found.",
        )
    return session

