import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from src.ai.factories.roadmap_factory import RoadmapChainFactory
# pyrefly: ignore [missing-import]
from src.db.base import SessionLocal
# pyrefly: ignore [missing-import]
from src.db.repositories.roadmap_repository import RoadmapRepository

# pyrefly: ignore [missing-import]
from src.schemas.roadmap import (
    RoadmapGenerationRequest,
    RoadmapRefreshRequest,
    RoadmapSchema,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class RoadmapService:
    """Service handling Roadmap generation, progress state machine, and adaptive updates."""

    async def create_roadmap(
        self,
        payload: RoadmapGenerationRequest,
        db: Optional[Session] = None,
    ) -> RoadmapSchema:
        chain = RoadmapChainFactory.for_role_family(
            role_family=payload.role_family or "Engineering"
        )
        roadmap = await chain.generate_roadmap(
            candidate_id=payload.candidate_id,
            target_role=payload.target_role,
            skill_gaps=payload.skill_gaps,
            role_family=payload.role_family,
        )

        # Persist to database
        session = db or SessionLocal()
        should_close = db is None
        try:
            repo = RoadmapRepository(session)
            repo.save_roadmap(roadmap)
        except Exception as err:
            logger.error("Failed to persist generated roadmap: %s", err, exc_info=True)
        finally:
            if should_close:
                session.close()

        return roadmap

    def get_candidate_roadmap(
        self,
        candidate_id: str,
        db: Optional[Session] = None,
    ) -> Optional[RoadmapSchema]:
        session = db or SessionLocal()
        should_close = db is None
        try:
            repo = RoadmapRepository(session)
            record = repo.get_by_candidate(candidate_id)
            if not record:
                return None
            return RoadmapSchema(**record.to_dict())
        finally:
            if should_close:
                session.close()

    def update_task_progress(
        self,
        candidate_id: str,
        task_id: str,
        new_status: TaskStatus,
        db: Optional[Session] = None,
    ) -> RoadmapSchema:
        session = db or SessionLocal()
        should_close = db is None
        try:
            repo = RoadmapRepository(session)
            record = repo.get_by_candidate(candidate_id)
            if not record:
                raise ValueError(f"No active roadmap found for candidate '{candidate_id}'.")

            roadmap = RoadmapSchema(**record.to_dict())
            task_found = False

            for phase in roadmap.phases:
                for milestone in phase.milestones:
                    for task in milestone.tasks:
                        if task.task_id == task_id:
                            task.status = new_status
                            task_found = True

                    # Recalculate milestone status based on its tasks
                    all_tasks = milestone.tasks
                    if all_tasks:
                        if all(t.status == TaskStatus.COMPLETED for t in all_tasks):
                            milestone.status = TaskStatus.COMPLETED
                        elif any(t.status in (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED) for t in all_tasks):
                            milestone.status = TaskStatus.IN_PROGRESS
                        else:
                            milestone.status = TaskStatus.NOT_STARTED

            if not task_found:
                raise ValueError(f"Task '{task_id}' not found in candidate roadmap.")

            roadmap.updated_at = datetime.utcnow().isoformat()
            repo.save_roadmap(roadmap)
            return roadmap
        finally:
            if should_close:
                session.close()

    async def refresh_roadmap(
        self,
        payload: RoadmapRefreshRequest,
        db: Optional[Session] = None,
    ) -> RoadmapSchema:
        session = db or SessionLocal()
        should_close = db is None
        try:
            repo = RoadmapRepository(session)
            existing_record = repo.get_by_candidate(payload.candidate_id)

            if not existing_record:
                # If no existing roadmap exists, generate a new one
                target_role = payload.target_role or "Software Engineer"
                gaps = payload.new_skill_gaps or ["Core Fundamentals"]
                return await self.create_roadmap(
                    RoadmapGenerationRequest(
                        candidate_id=payload.candidate_id,
                        target_role=target_role,
                        role_family=payload.role_family or "Engineering",
                        skill_gaps=gaps,
                    ),
                    db=session,
                )

            existing_roadmap = RoadmapSchema(**existing_record.to_dict())

            # Identify completed task IDs and skill gaps already fulfilled
            completed_gaps = set()
            for phase in existing_roadmap.phases:
                for ms in phase.milestones:
                    if all(t.status == TaskStatus.COMPLETED for t in ms.tasks):
                        completed_gaps.add(phase.cited_gap)

            updated_role = payload.target_role or existing_roadmap.target_role
            updated_family = payload.role_family or existing_roadmap.role_family

            if payload.new_skill_gaps is not None:
                remaining_gaps = [g for g in payload.new_skill_gaps if g not in completed_gaps]
            else:
                remaining_gaps = [p.cited_gap for p in existing_roadmap.phases if p.cited_gap not in completed_gaps]

            if not remaining_gaps:
                remaining_gaps = ["Advanced Career Progression"]

            new_roadmap = await self.create_roadmap(
                RoadmapGenerationRequest(
                    candidate_id=payload.candidate_id,
                    target_role=updated_role,
                    role_family=updated_family,
                    skill_gaps=remaining_gaps,
                ),
                db=session,
            )

            return new_roadmap
        finally:
            if should_close:
                session.close()


roadmap_service = RoadmapService()
