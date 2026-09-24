from __future__ import annotations

from src.db.repositories.base import BaseRepository
from src.db.repositories.behavior_repository import BehaviorRepository, MockBehaviorRepository
from src.db.repositories.candidate_repository import (
    CandidateRepository,
    MockCandidateRepository,
    candidate_repository,
)
from src.db.repositories.interview_repository import InterviewRepository
from src.db.repositories.job_repository import DatabaseJobRepository, JobRepository, UpsertOutcome
from src.db.repositories.job_requirement_repository import JobRequirementRepository
from src.db.repositories.match_repository import MatchRepository
from src.db.repositories.mock_job_repository import MockJobRepository
from src.db.repositories.review_queue_repository import ReviewQueueRepository
from src.db.repositories.roadmap_repository import RoadmapRepository

__all__ = [
    "BaseRepository",
    "BehaviorRepository",
    "MockBehaviorRepository",
    "CandidateRepository",
    "MockCandidateRepository",
    "candidate_repository",
    "InterviewRepository",
    "JobRepository",
    "DatabaseJobRepository",
    "UpsertOutcome",
    "JobRequirementRepository",
    "MatchRepository",
    "MockJobRepository",
    "ReviewQueueRepository",
    "RoadmapRepository",
]
