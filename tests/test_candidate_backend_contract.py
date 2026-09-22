from __future__ import annotations

from src.models.candidate import Candidate, CVExtractionSchema


def test_candidate_json_contract_is_unchanged():
    candidate = Candidate(candidate_id="cand_contract")
    assert set(candidate.model_dump()) == {
        "candidate_id", "user", "candidate_profile", "educations", "experiences",
        "projects", "certificates", "languages", "candidate_skills", "target_roles", "preferences",
    }


def test_extraction_schema_retains_existing_alias_and_null_collection_handling():
    extraction = CVExtractionSchema.model_validate({"name": "Avery", "raw_skills": None, "experience": None})
    assert extraction.user.name == "Avery"
    assert extraction.raw_skills == []
    assert extraction.experiences == []
