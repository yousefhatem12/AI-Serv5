from __future__ import annotations
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.schemas.application_strategy import (
    ApplicationStrategyRequest,
    ApplicationStrategyResponse,
    StrategyDecision,
    GapSeverity,
    GapItem,
    StrategyActionItem,
    AlternativeRole,
)
from src.services.application_strategy_service import (
    application_strategy_service,
    DISCLAIMER_TEXT,
)
from src.ai.crew.tools.strategy_tool import get_application_strategy_tool

client = TestClient(app)


def test_strategy_schema_validation():
    resp = ApplicationStrategyResponse(
        candidate_id="cand_001",
        job_id="job_001",
        job_title="Backend Engineer",
        decision=StrategyDecision.APPLY_NOW,
        match_score=0.88,
        summary_reasoning="Strong profile match.",
        strengths=["Python (95% match)", "FastAPI (90% match)"],
        blocker_gaps=[],
        manageable_gaps=[],
        action_plan=[
            StrategyActionItem(
                task="Apply to role immediately.",
                category="application",
                timeframe="Week 1",
                impact="High",
            )
        ],
        alternative_roles=[],
    )
    assert resp.decision == StrategyDecision.APPLY_NOW
    assert resp.match_score == 0.88
    assert "not a guarantee of hiring outcomes" in resp.disclaimer.lower()


def test_decision_matrix_apply_now():
    custom_profile = {
        "candidate_id": "cand_high",
        "skills": [
            {"skill_name": "Python", "match_score": 95.0, "is_matched": True},
            {"skill_name": "FastAPI", "match_score": 90.0, "is_matched": True},
            {"skill_name": "PostgreSQL", "match_score": 85.0, "is_matched": True},
        ],
    }
    custom_job = {
        "id": "job_high",
        "title": "Senior Python Developer",
        "required_skills": [
            {"skill_name": "Python", "is_critical": True},
            {"skill_name": "FastAPI", "is_critical": True},
            {"skill_name": "PostgreSQL", "is_critical": False},
        ],
    }
    strategy = application_strategy_service.generate_strategy(
        user_id="cand_high",
        job_id="job_high",
        custom_profile=custom_profile,
        custom_job=custom_job,
    )
    assert strategy.decision == StrategyDecision.APPLY_NOW
    assert strategy.match_score >= 0.75
    assert len(strategy.blocker_gaps) == 0
    assert len(strategy.action_plan) > 0
    assert "not a guarantee of hiring outcomes" in strategy.disclaimer.lower()


def test_decision_matrix_apply_while_improving():
    custom_profile = {
        "candidate_id": "cand_mid",
        "skills": [
            {"skill_name": "Python", "match_score": 85.0, "is_matched": True},
            {"skill_name": "Docker", "match_score": 55.0, "is_matched": False},
        ],
    }
    custom_job = {
        "id": "job_mid",
        "title": "Backend Developer",
        "required_skills": [
            {"skill_name": "Python", "is_critical": True},
            {"skill_name": "Docker", "is_critical": False},
            {"skill_name": "Redis", "is_critical": False},
        ],
    }
    strategy = application_strategy_service.generate_strategy(
        user_id="cand_mid",
        job_id="job_mid",
        custom_profile=custom_profile,
        custom_job=custom_job,
    )
    assert strategy.decision in [StrategyDecision.APPLY_WHILE_IMPROVING, StrategyDecision.PRIORITIZE_ANOTHER_ROLE]
    assert len(strategy.action_plan) > 0
    assert len(strategy.alternative_roles) > 0


def test_decision_matrix_prioritize_another_role():
    custom_profile = {
        "candidate_id": "cand_low",
        "skills": [
            {"skill_name": "HTML", "match_score": 70.0, "is_matched": True},
        ],
    }
    custom_job = {
        "id": "job_low",
        "title": "Cloud Infrastructure Architect",
        "required_skills": [
            {"skill_name": "Kubernetes", "is_critical": True},
            {"skill_name": "Terraform", "is_critical": True},
            {"skill_name": "AWS", "is_critical": True},
        ],
    }
    strategy = application_strategy_service.generate_strategy(
        user_id="cand_low",
        job_id="job_low",
        custom_profile=custom_profile,
        custom_job=custom_job,
    )
    assert strategy.decision == StrategyDecision.PRIORITIZE_ANOTHER_ROLE
    assert len(strategy.blocker_gaps) >= 1
    assert len(strategy.alternative_roles) > 0


def test_disclaimer_mandatory_and_no_guarantee():
    strategy = application_strategy_service.generate_strategy(
        user_id="cand_001",
        job_id="job_001",
    )
    assert strategy.disclaimer == DISCLAIMER_TEXT
    assert "not a guarantee of hiring outcomes" in strategy.disclaimer


def test_api_evaluate_strategy_endpoint():
    payload = {
        "user_id": "cand_001",
        "job_id": "job_001",
        "target_role": "Backend Engineer",
    }
    response = client.post("/api/v1/strategy/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "decision" in data
    assert "match_score" in data
    assert "summary_reasoning" in data
    assert "action_plan" in data
    assert "disclaimer" in data


def test_api_evaluate_job_strategy_endpoint():
    payload = {
        "user_id": "cand_001",
        "target_role": "Backend Engineer",
    }
    response = client.post("/api/v1/strategy/jobs/job_001", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job_001"
    assert data["decision"] in ["apply_now", "apply_while_improving", "prioritize_another_role"]


def test_crew_strategy_tool_execution():
    tool_res = get_application_strategy_tool.func(user_id="cand_001", job_id="job_001")
    assert isinstance(tool_res, dict)
    assert "decision" in tool_res
    assert "action_plan" in tool_res
    assert "disclaimer" in tool_res


def test_crew_strategy_tool_default_job_handling():
    """Verifies that the tool works when user asks generally without specifying job_id."""
    tool_res = get_application_strategy_tool.func(user_id="cand_001")
    assert isinstance(tool_res, dict)
    assert "decision" in tool_res
    assert "action_plan" in tool_res
    assert tool_res["decision"] in ["apply_now", "apply_while_improving", "prioritize_another_role"]
    assert "not a guarantee of hiring outcomes" in tool_res["disclaimer"].lower()

