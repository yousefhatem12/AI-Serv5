from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.schemas.job import SkillRequirement, JobPosting
from src.schemas.match import (
    SkillGapAnalysisRequest,
    SkillGapAnalysisResponse,
    SkillMatchItem,
    CandidateProfilePayload,
    QualificationStatus,
)
from src.services.matching_service import MatchingService

def test_normalize_job_requirements():
    service = MatchingService()

    # From string list
    reqs_str = ["Python", "FastAPI", "Docker"]
    normalized = service.normalize_job_requirements(reqs_str)
    assert len(normalized) == 3
    assert all(isinstance(r, SkillRequirement) for r in normalized)
    assert normalized[0].skill_name == "Python"

    # From dict list
    reqs_dict = [
        {"name": "Python", "proficiency": "Expert", "is_critical": True},
        {"skill_name": "Kubernetes", "proficiency": "Intermediate", "is_critical": False}
    ]
    normalized = service.normalize_job_requirements(reqs_dict)
    assert len(normalized) == 2
    assert normalized[0].is_critical is True
    assert normalized[1].skill_name == "Kubernetes"

    # From JobPosting
    posting = JobPosting(
        job_id="job_1",
        title="ML Engineer",
        required_skills=[
            SkillRequirement(skill_name="PyTorch", proficiency="Expert", is_critical=True)
        ]
    )
    normalized = service.normalize_job_requirements(posting)
    assert len(normalized) == 1
    assert normalized[0].skill_name == "PyTorch"

def test_apply_evaluation_rules_qualified():
    service = MatchingService()
    required_skills = [
        SkillRequirement(skill_name="Python", proficiency="Advanced", is_critical=True),
        SkillRequirement(skill_name="FastAPI", proficiency="Advanced", is_critical=True),
        SkillRequirement(skill_name="PostgreSQL", proficiency="Intermediate", is_critical=False),
    ]

    # Both critical skills matched >= 70, overall average >= 75
    raw_response = SkillGapAnalysisResponse(
        job_id="job_1",
        candidate_id="cand_1",
        overall_match_score=0.0,
        qualification_status=QualificationStatus.NOT_QUALIFIED,
        full_candidate_summary="Ready for hire.",
        skill_breakdown=[
            SkillMatchItem(
                skill_name="Python",
                required_proficiency="Advanced",
                candidate_proficiency="Expert",
                match_score=100.0,
                is_matched=True,
                skill_feedback="Strong production background.",
                evidence_found="5 years Python experience."
            ),
            SkillMatchItem(
                skill_name="FastAPI",
                required_proficiency="Advanced",
                candidate_proficiency="Intermediate",
                match_score=75.0,
                is_matched=True,
                skill_feedback="Good working knowledge.",
                evidence_found="Built 3 APIs."
            ),
            SkillMatchItem(
                skill_name="PostgreSQL",
                required_proficiency="Intermediate",
                candidate_proficiency="Basic",
                match_score=50.0,
                is_matched=False,
                skill_feedback="Basic query writing.",
                evidence_found="Academic exposure."
            ),
        ],
        missing_critical_skills=[],
        recommended_upskilling_path=[]
    )

    evaluated = service.apply_evaluation_rules(raw_response, required_skills)
    assert evaluated.overall_match_score == round((100 + 75 + 50) / 3, 1)  # 75.0
    assert evaluated.qualification_status == QualificationStatus.QUALIFIED
    # Critical skills: Python (100 >= 70), FastAPI (75 >= 70) => 100% critical match
    assert evaluated.missing_critical_skills == []

def test_apply_evaluation_rules_partially_qualified():
    service = MatchingService()
    required_skills = [
        SkillRequirement(skill_name="Go", proficiency="Advanced", is_critical=True),
        SkillRequirement(skill_name="Kubernetes", proficiency="Advanced", is_critical=True),
        SkillRequirement(skill_name="Docker", proficiency="Intermediate", is_critical=False),
        SkillRequirement(skill_name="Terraform", proficiency="Intermediate", is_critical=False),
    ]

    # Only 1 of 2 critical skills matched (50% critical match), overall average 62.5
    raw_response = SkillGapAnalysisResponse(
        job_id="job_2",
        candidate_id="cand_2",
        overall_match_score=0.0,
        qualification_status=QualificationStatus.NOT_QUALIFIED,
        full_candidate_summary="Needs upskilling.",
        skill_breakdown=[
            SkillMatchItem(
                skill_name="Go",
                required_proficiency="Advanced",
                candidate_proficiency="Advanced",
                match_score=100.0,
                is_matched=True,
                skill_feedback="Direct match.",
                evidence_found="Go services."
            ),
            SkillMatchItem(
                skill_name="Kubernetes",
                required_proficiency="Advanced",
                candidate_proficiency="None",
                match_score=0.0,
                is_matched=False,
                skill_feedback="Missing skill.",
                evidence_found="None."
            ),
            SkillMatchItem(
                skill_name="Docker",
                required_proficiency="Intermediate",
                candidate_proficiency="Intermediate",
                match_score=75.0,
                is_matched=True,
                skill_feedback="Moderate match.",
                evidence_found="Docker containers used."
            ),
            SkillMatchItem(
                skill_name="Terraform",
                required_proficiency="Intermediate",
                candidate_proficiency="Basic",
                match_score=75.0,
                is_matched=True,
                skill_feedback="Basic IaC exposure.",
                evidence_found="Small scripts."
            ),
        ],
        missing_critical_skills=[],
        recommended_upskilling_path=[]
    )

    evaluated = service.apply_evaluation_rules(raw_response, required_skills)
    assert evaluated.qualification_status == QualificationStatus.PARTIALLY_QUALIFIED
    assert "Kubernetes" in evaluated.missing_critical_skills

def test_apply_evaluation_rules_not_qualified():
    service = MatchingService()
    required_skills = [
        SkillRequirement(skill_name="Rust", proficiency="Advanced", is_critical=True),
        SkillRequirement(skill_name="WebAssembly", proficiency="Advanced", is_critical=True),
        SkillRequirement(skill_name="C++", proficiency="Intermediate", is_critical=False),
    ]

    raw_response = SkillGapAnalysisResponse(
        job_id="job_3",
        candidate_id="cand_3",
        overall_match_score=0.0,
        qualification_status=QualificationStatus.QUALIFIED,
        full_candidate_summary="Major gaps.",
        skill_breakdown=[
            SkillMatchItem(
                skill_name="Rust",
                required_proficiency="Advanced",
                candidate_proficiency="Basic",
                match_score=50.0,
                is_matched=False,
                skill_feedback="Basic familiarity.",
                evidence_found="Tutorial code."
            ),
            SkillMatchItem(
                skill_name="WebAssembly",
                required_proficiency="Advanced",
                candidate_proficiency="None",
                match_score=0.0,
                is_matched=False,
                skill_feedback="Not found.",
                evidence_found="None."
            ),
            SkillMatchItem(
                skill_name="C++",
                required_proficiency="Intermediate",
                candidate_proficiency="None",
                match_score=0.0,
                is_matched=False,
                skill_feedback="Not found.",
                evidence_found="None."
            ),
        ],
        missing_critical_skills=[],
        recommended_upskilling_path=[]
    )

    evaluated = service.apply_evaluation_rules(raw_response, required_skills)
    assert evaluated.qualification_status == QualificationStatus.NOT_QUALIFIED
    assert evaluated.overall_match_score == round(50.0 / 3, 1)  # 16.7
    assert "Rust" in evaluated.missing_critical_skills
    assert "WebAssembly" in evaluated.missing_critical_skills

@pytest.mark.asyncio
async def test_matching_service_analyze_skill_gap_mock_chain():
    mock_chain = MagicMock()
    mock_chain.analyze_skill_gap = AsyncMock(return_value=SkillGapAnalysisResponse(
        job_id="job_ai_1",
        candidate_id="cand_ai_1",
        overall_match_score=85.0,
        qualification_status=QualificationStatus.QUALIFIED,
        full_candidate_summary="Candidate is well prepared with excellent Python experience.",
        skill_breakdown=[
            SkillMatchItem(
                skill_name="Python",
                required_proficiency="Advanced",
                candidate_proficiency="Expert",
                match_score=100.0,
                is_matched=True,
                skill_feedback="Direct match.",
                evidence_found="5 years experience."
            ),
            SkillMatchItem(
                skill_name="FastAPI",
                required_proficiency="Intermediate",
                candidate_proficiency="Intermediate",
                match_score=75.0,
                is_matched=True,
                skill_feedback="Solid working knowledge.",
                evidence_found="FastAPI projects."
            )
        ],
        missing_critical_skills=[],
        recommended_upskilling_path=["Study advanced async concurrency patterns."]
    ))

    service = MatchingService(chains=mock_chain)

    req = SkillGapAnalysisRequest(
        job_id="job_ai_1",
        candidate_id="cand_ai_1",
        job_requirements=[
            {"name": "Python", "proficiency": "Advanced", "is_critical": True},
            {"name": "FastAPI", "proficiency": "Intermediate", "is_critical": True}
        ],
        candidate_profile=CandidateProfilePayload(
            candidate_id="cand_ai_1",
            skills=["Python", "FastAPI"]
        )
    )

    res = await service.analyze_skill_gap(req)
    assert res.job_id == "job_ai_1"
    assert res.candidate_id == "cand_ai_1"
    assert res.qualification_status == QualificationStatus.QUALIFIED
    assert len(res.skill_breakdown) == 2
    assert res.overall_match_score == 87.5
    assert mock_chain.analyze_skill_gap.called


def test_apply_evaluation_rules_prevents_hiding_omitted_critical_skills():
    """
    Test Blocker Fix: When the chain response omits requirements,
    post-processing MUST NOT calculate scoring/verdict from only the returned items.
    All required skills must be evaluated, and omitted critical skills must be flagged.
    """
    service = MatchingService()
    required_skills = [
        SkillRequirement(skill_name="Python", proficiency="Advanced", is_critical=True),
        SkillRequirement(skill_name="FastAPI", proficiency="Advanced", is_critical=True),
        SkillRequirement(skill_name="Docker", proficiency="Intermediate", is_critical=True),
        SkillRequirement(skill_name="Kubernetes", proficiency="Intermediate", is_critical=True),
        SkillRequirement(skill_name="AWS", proficiency="Intermediate", is_critical=True),
    ]

    # LLM returns only 2 out of 5 skills, both with 100% score
    partial_llm_response = SkillGapAnalysisResponse(
        job_id="job_partial",
        candidate_id="cand_partial",
        overall_match_score=100.0,
        qualification_status=QualificationStatus.QUALIFIED,
        full_candidate_summary="Strong Python backend developer.",
        skill_breakdown=[
            SkillMatchItem(
                skill_name="Python",
                required_proficiency="Advanced",
                candidate_proficiency="Expert",
                match_score=100.0,
                is_matched=True,
                skill_feedback="Direct match.",
                evidence_found="5 years experience."
            ),
            SkillMatchItem(
                skill_name="FastAPI",
                required_proficiency="Advanced",
                candidate_proficiency="Expert",
                match_score=100.0,
                is_matched=True,
                skill_feedback="Direct match.",
                evidence_found="Built FastAPI microservices."
            ),
        ],
        missing_critical_skills=[],
        recommended_upskilling_path=[]
    )

    evaluated = service.apply_evaluation_rules(partial_llm_response, required_skills)

    # 1. All 5 required skills MUST be present in breakdown (none omitted)
    breakdown_names = [item.skill_name for item in evaluated.skill_breakdown]
    assert len(evaluated.skill_breakdown) == 5
    assert set(breakdown_names) == {"Python", "FastAPI", "Docker", "Kubernetes", "AWS"}

    # 2. The 3 omitted skills must have match_score == 0.0 and is_matched == False
    omitted_items = {item.skill_name: item for item in evaluated.skill_breakdown if item.skill_name in {"Docker", "Kubernetes", "AWS"}}
    for name, item in omitted_items.items():
        assert item.match_score == 0.0
        assert item.is_matched is False
        assert item.candidate_proficiency == "Missing"
        assert f"Missing required skill: {name}" in item.skill_feedback

    # 3. Critical gaps CANNOT be hidden: missing_critical_skills must list all 3 omitted critical skills
    assert "Docker" in evaluated.missing_critical_skills
    assert "Kubernetes" in evaluated.missing_critical_skills
    assert "AWS" in evaluated.missing_critical_skills

    # 4. Overall match score must average across ALL 5 requirements (40.0, not 100.0!)
    assert evaluated.overall_match_score == 40.0

    # 5. Verdict CANNOT be Qualified (only 2/5 = 40% critical match, avg 40.0 < 50.0) -> Not Qualified
    assert evaluated.qualification_status == QualificationStatus.NOT_QUALIFIED

    # 6. Recommended upskilling path must address the missing critical skills
    upskilling_str = " ".join(evaluated.recommended_upskilling_path)
    assert "Docker" in upskilling_str
    assert "Kubernetes" in upskilling_str
    assert "AWS" in upskilling_str


@pytest.mark.asyncio
async def test_analyze_skill_gap_end_to_end_synthesizes_omitted_chain_requirements():
    """Verify that MatchingService.analyze_skill_gap guarantees all requirements in end-to-end flow."""
    mock_chain = MagicMock()
    # Mock chain returns incomplete response
    mock_chain.analyze_skill_gap = AsyncMock(return_value=SkillGapAnalysisResponse(
        job_id="job_e2e",
        candidate_id="cand_e2e",
        overall_match_score=90.0,
        qualification_status=QualificationStatus.QUALIFIED,
        full_candidate_summary="Candidate has SQL experience.",
        skill_breakdown=[
            SkillMatchItem(
                skill_name="SQL",
                required_proficiency="Advanced",
                candidate_proficiency="Advanced",
                match_score=90.0,
                is_matched=True,
                skill_feedback="Strong SQL skills.",
                evidence_found="Database administrator background."
            )
        ],
        missing_critical_skills=[],
        recommended_upskilling_path=[]
    ))

    service = MatchingService(chains=mock_chain)

    req = SkillGapAnalysisRequest(
        job_id="job_e2e",
        candidate_id="cand_e2e",
        job_requirements=[
            {"skill_name": "SQL", "proficiency": "Advanced", "is_critical": True},
            {"skill_name": "PostgreSQL", "proficiency": "Intermediate", "is_critical": True},
            {"skill_name": "Kafka", "proficiency": "Intermediate", "is_critical": False},
        ],
        candidate_profile=CandidateProfilePayload(
            candidate_id="cand_e2e",
            skills=["SQL"]
        )
    )

    res = await service.analyze_skill_gap(req)
    assert len(res.skill_breakdown) == 3
    assert "PostgreSQL" in res.missing_critical_skills
    # PostgreSQL (0) and Kafka (0), SQL (90) -> avg = 30.0
    assert res.overall_match_score == 30.0
    assert res.qualification_status == QualificationStatus.NOT_QUALIFIED


@pytest.mark.asyncio
async def test_explainable_match_covers_all_dimensions():
    """Verify Explainable Job Match covers role alignment, experience, preferences, and preferred skills."""
    mock_chain = MagicMock()
    mock_chain.analyze_skill_gap = AsyncMock(return_value=SkillGapAnalysisResponse(
        job_id="job_dim_1",
        candidate_id="cand_dim_1",
        overall_match_score=100.0,
        qualification_status=QualificationStatus.QUALIFIED,
        full_candidate_summary="Expert candidate.",
        skill_breakdown=[
            SkillMatchItem(
                skill_name="Python",
                required_proficiency="Advanced",
                candidate_proficiency="Expert",
                match_score=100.0,
                is_matched=True,
                skill_feedback="Strong Python match.",
                evidence_found="Years of Python backend development."
            ),
            SkillMatchItem(
                skill_name="PostgreSQL",
                required_proficiency="Intermediate",
                candidate_proficiency="Intermediate",
                match_score=80.0,
                is_matched=True,
                skill_feedback="Good database experience.",
                evidence_found="Designed relational schemas."
            )
        ],
        missing_critical_skills=[],
        recommended_upskilling_path=[]
    ))

    service = MatchingService(chains=mock_chain)

    req = SkillGapAnalysisRequest(
        job_id="job_dim_1",
        candidate_id="cand_dim_1",
        job_title="Senior Backend Engineer",
        canonical_role="Backend Engineer",
        min_years_experience=5.0,
        work_mode="remote",
        location="Berlin",
        employment_type="full-time",
        job_requirements=[
            {"skill_name": "Python", "proficiency": "Advanced", "is_critical": True},
            {"skill_name": "PostgreSQL", "proficiency": "Intermediate", "is_critical": True}
        ],
        preferred_skills=["Docker", "Kubernetes"],
        candidate_profile=CandidateProfilePayload(
            candidate_id="cand_dim_1",
            target_roles=["Backend Engineer"],
            total_years_experience=6.0,
            preferences={
                "work_mode": "remote",
                "locations": ["Berlin"],
                "employment_type": "full-time"
            },
            skills=["Python", "PostgreSQL", "Docker"]
        )
    )

    res = await service.explain_job_match(req)

    # 1. Assert all 5 dimension scores are calculated
    assert res.skills_match_score == 90.0  # (100 + 80) / 2
    assert res.role_alignment_score == 100.0  # Exact match on Backend Engineer
    assert res.experience_score == 100.0  # 6.0 >= 5.0 years
    assert res.preference_fit_score == 100.0  # Remote + Berlin + Full-time
    assert res.score_breakdown is not None
    assert set(res.score_breakdown.keys()) == {
        "skills_match", "role_alignment", "experience", "preference_fit", "preferred_skills"
    }

    # 2. Preferred skills breakdown & gaps
    assert len(res.preferred_skills_breakdown) == 2
    # Docker matched (candidate has Docker)
    docker_item = next(p for p in res.preferred_skills_breakdown if p.skill_name == "Docker")
    assert docker_item.is_matched is True
    assert docker_item.match_score == 100.0
    # Kubernetes not matched
    k8s_item = next(p for p in res.preferred_skills_breakdown if p.skill_name == "Kubernetes")
    assert k8s_item.is_matched is False
    assert k8s_item.match_score == 0.0
    assert "Kubernetes" in res.nice_to_have_gaps

    # 3. Preferred skills score: (100 + 0) / 2 = 50.0
    assert res.score_breakdown["preferred_skills"] == 50.0

    # 4. Composite score:
    # 90 * 0.50 + 100 * 0.20 + 100 * 0.15 + 100 * 0.10 + 50 * 0.05
    # = 45.0 + 20.0 + 15.0 + 10.0 + 2.5 = 92.5
    assert res.overall_match_score == 92.5

    # 5. Metadata and rationale
    assert res.priority == "high"
    assert "high hiring priority" in res.rationale
    assert "Skills Match: 90.0%" in res.rationale
    assert len(res.blockers) == 0


@pytest.mark.asyncio
async def test_explainable_match_experience_and_critical_blockers():
    """Verify that severe experience gaps and missing critical skills generate blockers and downgrade verdict."""
    mock_chain = MagicMock()
    mock_chain.analyze_skill_gap = AsyncMock(return_value=SkillGapAnalysisResponse(
        job_id="job_blocker",
        candidate_id="cand_blocker",
        overall_match_score=50.0,
        qualification_status=QualificationStatus.NOT_QUALIFIED,
        full_candidate_summary="Junior candidate.",
        skill_breakdown=[
            SkillMatchItem(
                skill_name="Python",
                required_proficiency="Senior",
                candidate_proficiency="Beginner",
                match_score=40.0,
                is_matched=False,
                skill_feedback="Partial skills.",
                evidence_found="Small script."
            )
        ],
        missing_critical_skills=["Python"],
        recommended_upskilling_path=["Master advanced Python."]
    ))

    service = MatchingService(chains=mock_chain)

    req = SkillGapAnalysisRequest(
        job_id="job_blocker",
        candidate_id="cand_blocker",
        job_title="Lead Architect",
        min_years_experience=8.0,
        job_requirements=[
            {"skill_name": "Python", "proficiency": "Senior", "is_critical": True}
        ],
        candidate_profile=CandidateProfilePayload(
            candidate_id="cand_blocker",
            target_roles=["Junior Developer"],
            total_years_experience=1.0,  # 1.0 < 8.0 * 0.5 -> blocker
            skills=["Python"]
        )
    )

    res = await service.explain_job_match(req)

    # Experience score for 1.0 yr vs 8.0 yrs
    assert res.experience_score <= 50.0
    # Blockers should include both missing critical skill and experience deficit
    assert any("Insufficient experience" in b for b in res.blockers)
    assert any("Missing critical skill: Python" in b for b in res.blockers)
    # Weak skills should capture Python (match_score=40.0)
    assert "Python" in res.weak_skills
    # Low priority
    assert res.priority == "low"
    assert res.qualification_status == QualificationStatus.NOT_QUALIFIED

