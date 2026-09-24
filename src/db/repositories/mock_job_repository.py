from __future__ import annotations
"""Mock Job Repository implementation backed by static seed fixtures."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.db.repositories.job_repository import JobRepository
from src.schemas.job import JobPosting, SkillRequirement

logger = logging.getLogger(__name__)


def _parse_iso_datetime(dt_val: Any) -> Optional[datetime]:
    """Helper to safely parse ISO timestamp strings into datetime objects."""
    if isinstance(dt_val, datetime):
        return dt_val
    if isinstance(dt_val, str) and dt_val.strip():
        try:
            clean_str = dt_val.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_str)
        except Exception:
            return None
    return None


class MockJobRepository(JobRepository):
    """
    In-memory mock job repository that reads from jobs_seed.json.
    Completely candidate-agnostic, supporting standard catalog queries.
    """

    def __init__(self, seed_path: Optional[Union[str, Path]] = None):
        if seed_path is None:
            base_dir = Path(__file__).resolve().parents[3]
            candidate_paths = [
                base_dir / "tests" / "fixtures" / "jobs_seed.json",
                base_dir / "fixtures" / "jobs_seed.json",
                base_dir / "src" / "fixtures" / "jobs_seed.json",
            ]
            self.seed_path = next((p for p in candidate_paths if p.exists()), candidate_paths[0])
        else:
            self.seed_path = Path(seed_path)

        self._jobs: Dict[str, JobPosting] = {}
        self._load_seed_data()

    def _load_seed_data(self) -> None:
        """Loads and parses raw JSON jobs into validated JobPosting models."""
        if not self.seed_path.exists():
            logger.warning(f"Mock job seed file not found at '{self.seed_path}'. Initializing empty catalog.")
            return

        try:
            with open(self.seed_path, "r", encoding="utf-8") as f:
                raw_list = json.load(f)

            for raw_job in raw_list:
                job_id = raw_job.get("job_id")
                if not job_id:
                    continue

                raw_skills = raw_job.get("required_skills", [])
                parsed_skills = []
                for s in raw_skills:
                    if isinstance(s, dict):
                        parsed_skills.append(
                            SkillRequirement(
                                skill_name=s.get("skill_name", "Unknown"),
                                proficiency=s.get("proficiency", "Intermediate"),
                                is_critical=s.get("is_critical", False),
                                category=s.get("category"),
                                min_years_experience=s.get("min_years_experience"),
                                description=s.get("description"),
                            )
                        )
                    elif isinstance(s, str):
                        parsed_skills.append(SkillRequirement(skill_name=s))

                job_posting = JobPosting(
                    job_id=job_id,
                    title=raw_job.get("title", ""),
                    company=raw_job.get("company"),
                    role=raw_job.get("role"),
                    canonical_role=raw_job.get("canonical_role"),
                    role_family=raw_job.get("role_family"),
                    description=raw_job.get("description"),
                    department=raw_job.get("department"),
                    location=raw_job.get("location"),
                    work_mode=raw_job.get("work_mode", "remote"),
                    employment_type=raw_job.get("employment_type", "full_time"),
                    experience_level=raw_job.get("experience_level"),
                    min_years_experience=raw_job.get("min_years_experience"),
                    posted_at=_parse_iso_datetime(raw_job.get("posted_at")),
                    expires_at=_parse_iso_datetime(raw_job.get("expires_at")),
                    is_active=raw_job.get("is_active", True),
                    source_url=raw_job.get("source_url"),
                    salary=raw_job.get("salary"),
                    source=raw_job.get("source"),
                    source_external_id=raw_job.get("source_external_id"),
                    source_updated_at=_parse_iso_datetime(raw_job.get("source_updated_at")),
                    ingested_at=_parse_iso_datetime(raw_job.get("ingested_at")),
                    description_is_partial=raw_job.get("description_is_partial", False),
                    required_skills=parsed_skills,
                )
                self._jobs[job_id] = job_posting

        except Exception as e:
            logger.error(f"Failed to load mock jobs from '{self.seed_path}': {e}", exc_info=True)

    def get_active_jobs(
        self,
        work_mode: Optional[str] = None,
        location: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[JobPosting]:
        def _is_future(dt: Optional[datetime]) -> bool:
            if dt is None:
                return True
            if not isinstance(dt, datetime):
                return True
            if dt.tzinfo is not None:
                return dt > datetime.now(timezone.utc)
            return dt > datetime.utcnow()

        def _sort_key(x: JobPosting) -> datetime:
            dt = x.posted_at
            if not isinstance(dt, datetime):
                return datetime.min
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt

        active = [
            j for j in self._jobs.values()
            if j.is_active and _is_future(j.expires_at)
        ]

        if work_mode:
            active = [j for j in active if j.work_mode.lower() == work_mode.lower()]

        if location:
            active = [j for j in active if j.location and location.lower() in j.location.lower()]

        active.sort(key=_sort_key, reverse=True)

        paged = active[offset:]
        if limit is not None:
            paged = paged[:limit]

        return paged

    def get_job_by_id(self, job_id: str) -> Optional[JobPosting]:
        return self._jobs.get(job_id)

    def get_job(self, job_id: str) -> Optional[JobPosting]:
        return self.get_job_by_id(job_id)


mock_job_repository = MockJobRepository()
