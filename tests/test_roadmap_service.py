from __future__ import annotations
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.base import Base
import src.db.models.roadmap  # noqa: F401
from src.schemas.roadmap import (
    RoadmapGenerationRequest,
    RoadmapRefreshRequest,
    TaskStatus,
)
from src.services.roadmap_service import roadmap_service


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.mark.asyncio
async def test_roadmap_generation_and_persistence(test_db):
    request = RoadmapGenerationRequest(
        candidate_id="cand_test_101",
        target_role="Senior Backend Engineer",
        role_family="Backend Engineering",
        skill_gaps=["Docker", "Kubernetes", "Redis"],
    )

    roadmap = await roadmap_service.create_roadmap(request, db=test_db)

    assert roadmap.candidate_id == "cand_test_101"
    assert roadmap.target_role == "Senior Backend Engineer"
    assert len(roadmap.phases) == 3

    # Check grounding citation
    for phase in roadmap.phases:
        assert phase.cited_gap in ["Docker", "Kubernetes", "Redis"]

    # Verify retrieval from DB
    fetched = roadmap_service.get_candidate_roadmap("cand_test_101", db=test_db)
    assert fetched is not None
    assert fetched.candidate_id == "cand_test_101"
    assert len(fetched.phases) == 3


@pytest.mark.asyncio
async def test_task_status_state_machine(test_db):
    request = RoadmapGenerationRequest(
        candidate_id="cand_test_102",
        target_role="Data Engineer",
        role_family="Data",
        skill_gaps=["Apache Spark"],
    )
    roadmap = await roadmap_service.create_roadmap(request, db=test_db)

    task_id = roadmap.phases[0].milestones[0].tasks[0].task_id

    # Update status to in_progress
    updated = roadmap_service.update_task_progress(
        candidate_id="cand_test_102",
        task_id=task_id,
        new_status=TaskStatus.IN_PROGRESS,
        db=test_db,
    )
    assert updated.phases[0].milestones[0].status == TaskStatus.IN_PROGRESS

    # Complete all tasks in milestone
    for t in updated.phases[0].milestones[0].tasks:
        roadmap_service.update_task_progress(
            candidate_id="cand_test_102",
            task_id=t.task_id,
            new_status=TaskStatus.COMPLETED,
            db=test_db,
        )

    final_rm = roadmap_service.get_candidate_roadmap("cand_test_102", db=test_db)
    assert final_rm.phases[0].milestones[0].status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_roadmap_adaptation_refresh(test_db):
    request = RoadmapGenerationRequest(
        candidate_id="cand_test_103",
        target_role="Frontend Engineer",
        role_family="Frontend",
        skill_gaps=["TypeScript", "GraphQL"],
    )
    await roadmap_service.create_roadmap(request, db=test_db)

    # Refresh with new skill gaps
    refresh_req = RoadmapRefreshRequest(
        candidate_id="cand_test_103",
        new_skill_gaps=["Next.js", "Web Performance"],
    )
    refreshed = await roadmap_service.refresh_roadmap(refresh_req, db=test_db)

    assert refreshed.candidate_id == "cand_test_103"
    assert len(refreshed.phases) == 2
    cited_gaps = [p.cited_gap for p in refreshed.phases]
    assert "Next.js" in cited_gaps
    assert "Web Performance" in cited_gaps


@pytest.mark.asyncio
async def test_roadmap_enrichment(test_db):
    from src.db.models.skill_resource import SkillResourceModel
    
    # Insert a dummy resource
    resource = SkillResourceModel(
        skill_id="skill_docker",
        video_id="dummy_video_id_123",
        title="Docker Tutorial for Beginners",
        channel_name="Tech Channel",
        status="approved"
    )
    test_db.add(resource)
    test_db.commit()

    request = RoadmapGenerationRequest(
        candidate_id="cand_test_104",
        target_role="DevOps Engineer",
        role_family="DevOps",
        skill_gaps=["Docker"],
    )
    
    roadmap = await roadmap_service.create_roadmap(request, db=test_db)
    
    # Check if the resource was enriched
    found_resource = False
    for phase in roadmap.phases:
        for milestone in phase.milestones:
            for task in milestone.tasks:
                if any(link.video_id == "dummy_video_id_123" or link.url.endswith("dummy_video_id_123") for link in task.resource_links):
                    found_resource = True
                    break
    
    assert found_resource, "The roadmap should be enriched with the approved YouTube resource"


@pytest.mark.asyncio
async def test_roadmap_valid_json_text_success():
    from unittest.mock import AsyncMock, MagicMock
    from src.ai.chains.roadmap_chain import RoadmapGenerationChain
    from src.schemas.roadmap import RoadmapSchema

    mock_llm = MagicMock()
    valid_json = """
    {
        "roadmap_id": "rm_from_model",
        "candidate_id": "ignored_id",
        "target_role": "ignored_role",
        "role_family": "ignored_family",
        "total_weeks": 6,
        "phases": [
            {
                "phase_id": "p1",
                "title": "Docker Deep Dive",
                "order": 1,
                "cited_gap": "Docker",
                "rationale": "Foundation for containers",
                "milestones": [
                    {
                        "milestone_id": "m1",
                        "title": "Containers 101",
                        "target_week": 1,
                        "tasks": []
                    }
                ]
            }
        ]
    }
    """
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=valid_json))

    chain = RoadmapGenerationChain(llm=mock_llm, role_family="Engineering")
    result = await chain.generate_roadmap(
        candidate_id="cand_app_1",
        target_role="Platform Engineer",
        skill_gaps=["Docker"],
        role_family="Cloud Architecture",
    )

    assert isinstance(result, RoadmapSchema)
    assert result.generation_source == "llm"
    assert result.candidate_id == "cand_app_1"
    assert result.target_role == "Platform Engineer"
    assert result.role_family == "Cloud Architecture"
    assert len(result.phases) == 1
    assert result.phases[0].cited_gap == "Docker"


@pytest.mark.asyncio
async def test_roadmap_markdown_json_success():
    from unittest.mock import AsyncMock, MagicMock
    from src.ai.chains.roadmap_chain import RoadmapGenerationChain

    mock_llm = MagicMock()
    markdown_json = """```json
    {
        "phases": [
            {
                "phase_id": "p_k8s",
                "title": "Kubernetes Mastery",
                "order": 1,
                "cited_gap": "Kubernetes",
                "rationale": "Orchestration layer",
                "milestones": []
            }
        ],
        "total_weeks": 4
    }
    ```"""
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=markdown_json))

    chain = RoadmapGenerationChain(llm=mock_llm, role_family="Engineering")
    result = await chain.generate_roadmap(
        candidate_id="cand_k8s_2",
        target_role="DevOps Specialist",
        skill_gaps=["Kubernetes"],
        role_family="Infrastructure",
    )

    assert result.generation_source == "llm"
    assert result.candidate_id == "cand_k8s_2"
    assert result.target_role == "DevOps Specialist"
    assert result.role_family == "Infrastructure"
    assert len(result.phases) == 1
    assert result.phases[0].cited_gap == "Kubernetes"


@pytest.mark.asyncio
async def test_roadmap_invalid_json_fallback(caplog):
    import logging
    from unittest.mock import AsyncMock, MagicMock
    from src.ai.chains.roadmap_chain import RoadmapGenerationChain

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Here is your roadmap: NOT VALID JSON AT ALL"))

    chain = RoadmapGenerationChain(llm=mock_llm, role_family="Engineering")
    with caplog.at_level(logging.WARNING):
        result = await chain.generate_roadmap(
            candidate_id="cand_invalid_json",
            target_role="Data Engineer",
            skill_gaps=["Spark", "Kafka"],
            role_family="Data & Analytics",
        )

    assert result.generation_source == "deterministic_fallback"
    assert result.candidate_id == "cand_invalid_json"
    assert result.target_role == "Data Engineer"
    assert result.role_family == "Data & Analytics"
    assert len(result.phases) == 2
    assert [p.cited_gap for p in result.phases] == ["Spark", "Kafka"]
    assert any("Roadmap LLM JSON parsing failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_roadmap_schema_invalid_json_fallback(caplog):
    import logging
    from unittest.mock import AsyncMock, MagicMock
    from src.ai.chains.roadmap_chain import RoadmapGenerationChain

    mock_llm = MagicMock()
    invalid_schema_json = '{"roadmap_id": "rm_1", "phases": "NOT_A_LIST"}'
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=invalid_schema_json))

    chain = RoadmapGenerationChain(llm=mock_llm, role_family="Engineering")
    with caplog.at_level(logging.WARNING):
        result = await chain.generate_roadmap(
            candidate_id="cand_schema_err",
            target_role="Frontend Engineer",
            skill_gaps=["React", "TypeScript"],
            role_family="Frontend",
        )

    assert result.generation_source == "deterministic_fallback"
    assert result.candidate_id == "cand_schema_err"
    assert result.target_role == "Frontend Engineer"
    assert len(result.phases) == 2
    assert any("RoadmapSchema validation failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_roadmap_invocation_failure_fallback(caplog):
    import logging
    from unittest.mock import AsyncMock, MagicMock
    from src.ai.chains.roadmap_chain import RoadmapGenerationChain

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Provider 503 Service Unavailable"))

    chain = RoadmapGenerationChain(llm=mock_llm, role_family="Cloud Engineering")

    with caplog.at_level(logging.WARNING):
        result = await chain.generate_roadmap(
            candidate_id="cand_test_fallback",
            target_role="Cloud Architect",
            skill_gaps=["AWS", "Terraform"],
            role_family="Cloud Engineering",
        )

    assert result.generation_source == "deterministic_fallback"
    assert result.candidate_id == "cand_test_fallback"
    assert result.target_role == "Cloud Architect"
    assert result.role_family == "Cloud Engineering"
    assert len(result.phases) == 2
    assert [p.cited_gap for p in result.phases] == ["AWS", "Terraform"]
    assert any("Roadmap LLM invocation failed" in r.message for r in caplog.records)


def test_roadmap_chain_factory_role_families():
    from src.ai.factories.roadmap_factory import RoadmapChainFactory
    from src.ai.chains.roadmap_chain import RoadmapGenerationChain

    chain_data = RoadmapChainFactory.for_role_family("data science")
    assert isinstance(chain_data, RoadmapGenerationChain)
    assert chain_data.role_family == "Data & Analytics"
    assert chain_data._custom_llm is None

    chain_fe = RoadmapChainFactory.for_role_family("Frontend UI")
    assert isinstance(chain_fe, RoadmapGenerationChain)
    assert chain_fe.role_family == "Frontend Engineering"
    assert chain_fe._custom_llm is None

    chain_be = RoadmapChainFactory.for_role_family("Backend Developer")
    assert isinstance(chain_be, RoadmapGenerationChain)
    assert chain_be.role_family == "Backend Engineering"
    assert chain_be._custom_llm is None

    chain_gen = RoadmapChainFactory.for_role_family("Security Operations")
    assert isinstance(chain_gen, RoadmapGenerationChain)
    assert chain_gen.role_family == "General Technical"
    assert chain_gen._custom_llm is None
