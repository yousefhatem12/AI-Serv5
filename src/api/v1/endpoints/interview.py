from __future__ import annotations
"""FastAPI endpoint for the Interview Preparation Coach feature."""

from fastapi import APIRouter, status
from src.schemas.interview import (
    QuestionGenerationRequest,
    QuestionSetResponse,
    AnswerSubmission,
    AnswerEvaluationResponse,
)
from src.services.interview_service import interview_service

router = APIRouter(prefix="/interview", tags=["Interview Preparation Coach"])


@router.post("/generate", response_model=QuestionSetResponse, status_code=status.HTTP_200_OK)
async def generate_interview_questions(payload: QuestionGenerationRequest):
    return await interview_service.create_prep_session(payload)


@router.post("/evaluate", response_model=AnswerEvaluationResponse, status_code=status.HTTP_200_OK)
async def evaluate_interview_answer(payload: AnswerSubmission):
    return await interview_service.evaluate_submission(payload)
