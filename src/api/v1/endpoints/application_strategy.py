from __future__ import annotations
"""FastAPI endpoints for Application Strategy Guidance (Feature 10)."""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Body

from src.schemas.application_strategy import (
    ApplicationStrategyRequest,
    ApplicationStrategyResponse,
)
from src.services.application_strategy_service import application_strategy_service

router = APIRouter(prefix="/strategy", tags=["Application Strategy Guidance"])


@router.post(
    "/evaluate",
    response_model=ApplicationStrategyResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate application strategy: apply now, improve gaps, or prioritize another role",
)
async def evaluate_application_strategy(
    payload: ApplicationStrategyRequest,
) -> ApplicationStrategyResponse:
    """
    Evaluates candidate readiness for a specific target job.
    Returns a strategic decision, structured reasoning, blocker vs manageable gaps,
    an action plan, and alternative role suggestions.
    Framed strictly as professional advice with no hiring outcome guarantee.
    """
    try:
        return application_strategy_service.generate_strategy(
            user_id=payload.user_id,
            job_id=payload.job_id,
            target_role=payload.target_role,
            user_notes=payload.user_notes,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate application strategy: {str(e)}",
        )


@router.post(
    "/jobs/{job_id}",
    response_model=ApplicationStrategyResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate application strategy for a path-specified job",
)
async def evaluate_job_application_strategy(
    job_id: str,
    user_id: str = Body(..., embed=True, description="The candidate user ID"),
    target_role: Optional[str] = Body(None, embed=True),
    user_notes: Optional[str] = Body(None, embed=True),
) -> ApplicationStrategyResponse:
    """
    Convenience endpoint taking job_id in path and candidate details in body.
    """
    try:
        return application_strategy_service.generate_strategy(
            user_id=user_id,
            job_id=job_id,
            target_role=target_role,
            user_notes=user_notes,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate application strategy: {str(e)}",
        )
