from __future__ import annotations

import pytest

from src.cv_extractor.llm_extractor import CoverageValidationResult, CVExtractionIncompleteError, LLMExtractor


class SequencedLLM:
    def __init__(self, responses: list[dict]):
        self.responses = iter(responses)
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def generate_json(self, prompt: str, system_prompt: str) -> dict:
        self.calls += 1
        return next(self.responses)


def _clean() -> dict:
    return {
        "complete": True,
        "missing_paths": [],
        "unsupported_paths": [],
        "fidelity_paths": [],
    }


@pytest.mark.parametrize(
    ("source", "extraction"),
    [
        ("Role\nMay 2021", {"experiences": [{"job_title": "Role", "start_date": None}]}),
        ("Role\n2021", {"experiences": [{"job_title": "Role", "start_date": None}]}),
    ],
)
def test_partial_source_date_with_null_full_date_is_complete(source: str, extraction: dict):
    llm = SequencedLLM([extraction, _clean()])

    result = LLMExtractor(llm=llm).extract_entities(source)

    assert result["experiences"][0]["start_date"] is None
    assert llm.calls == 2


def test_explicit_full_date_with_null_field_is_missing():
    extraction = {"experiences": [{"job_title": "Role", "start_date": None}]}
    missing = {"complete": False, "missing_paths": ["experiences.0.start_date"], "unsupported_paths": []}
    llm = SequencedLLM([extraction, missing, extraction, missing])

    with pytest.raises(CVExtractionIncompleteError):
        LLMExtractor(llm=llm).extract_entities("Role\n15 May 2021")

    assert llm.calls == 4


def test_partial_source_date_with_fabricated_full_date_remains_a_fidelity_failure():
    fabricated = {"experiences": [{"job_title": "Role", "start_date": "2021-05-01"}]}
    corrected = {"experiences": [{"job_title": "Role", "start_date": None}]}
    fidelity_failure = {
        "complete": False,
        "missing_paths": [],
        "unsupported_paths": [],
        "fidelity_paths": ["experiences.0.start_date"],
    }
    llm = SequencedLLM([fabricated, fidelity_failure, corrected, _clean()])

    result = LLMExtractor(llm=llm).extract_entities("Role\nMay 2021")

    assert result["experiences"][0]["start_date"] is None
    assert llm.calls == 4


def test_absent_collection_with_empty_extraction_is_complete():
    llm = SequencedLLM([{"projects": []}, _clean()])

    result = LLMExtractor(llm=llm).extract_entities("Role only")

    assert result["projects"] == []
    assert llm.calls == 2


def test_source_supported_collection_record_with_empty_extraction_is_missing():
    extraction = {"projects": []}
    missing = {"complete": False, "missing_paths": ["projects"], "unsupported_paths": []}
    llm = SequencedLLM([extraction, missing, extraction, missing])

    with pytest.raises(CVExtractionIncompleteError):
        LLMExtractor(llm=llm).extract_entities("Project Record")

    assert llm.calls == 4


def test_nullable_field_without_source_supported_value_is_complete():
    llm = SequencedLLM([{"candidate_profile": {"phone": None}}, _clean()])

    result = LLMExtractor(llm=llm).extract_entities("Candidate")

    assert result["candidate_profile"]["phone"] is None
    assert llm.calls == 2


def test_nullable_field_with_explicit_source_value_is_missing():
    extraction = {"candidate_profile": {"phone": None}}
    missing = {"complete": False, "missing_paths": ["candidate_profile.phone"], "unsupported_paths": []}
    llm = SequencedLLM([extraction, missing, extraction, missing])

    with pytest.raises(CVExtractionIncompleteError):
        LLMExtractor(llm=llm).extract_entities("Phone: 123456")

    assert llm.calls == 4


def test_unsupported_value_remains_a_fidelity_failure():
    extraction = {"candidate_profile": {"phone": "123456"}}
    unsupported = {"complete": False, "missing_paths": [], "unsupported_paths": ["candidate_profile.phone"]}
    llm = SequencedLLM([extraction, unsupported, extraction, unsupported])

    with pytest.raises(CVExtractionIncompleteError):
        LLMExtractor(llm=llm).extract_entities("Candidate")

    assert llm.calls == 4


def test_validator_paths_use_canonical_bracket_indices_for_paths_and_reasons():
    validation = CoverageValidationResult(
        complete=False,
        missing_paths=["records.0.value"],
        finding_reasons={"records.0.value": "explicit source-supported value omitted"},
    )

    assert validation.missing_paths == ["records[0].value"]
    assert validation.finding_reasons == {"records[0].value": "explicit source-supported value omitted"}
