from __future__ import annotations

import concurrent.futures
import logging

import pytest

from src.cv_extractor.llm_extractor import (
    CVExtractionError,
    CVExtractionIncompleteError,
    LLMExtractor,
)
from src.cv_extractor.pipeline import CVExtractionPipeline


class SequencedLLM:
    """Test double for the centralized JSON invocation interface."""

    def __init__(self, responses: list[object], available: bool = True):
        self.responses = iter(responses)
        self.available = available
        self.prompts: list[str] = []
        self.system_prompts: list[str] = []

    def is_available(self) -> bool:
        return self.available

    def generate_json(self, prompt: str, system_prompt: str):
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def _candidate() -> dict:
    return {
        "user": {"name": "Avery", "email": "avery@example.test"},
        "candidate_profile": {"headline": "Contributor"},
        "raw_skills": [{"name": "Tool-Alpha"}],
        "projects": [{"title": "Record One", "description": "Explicit work"}],
    }


def _complete() -> dict:
    return {"complete": True, "missing_paths": [], "unsupported_paths": []}


def _incomplete(*paths: str) -> dict:
    return {"complete": False, "missing_paths": list(paths), "unsupported_paths": []}


def test_complete_extraction_is_returned_without_retry_and_uses_full_source():
    source = "Avery\n" + ("record\n" * 7000) + "terminal explicit value"
    llm = SequencedLLM([_candidate(), _complete()])

    result = LLMExtractor(llm=llm).extract_entities(source, sections={"arbitrary": "ignored"})

    assert result.extraction_mode == "llm"
    assert result["user"]["email"] == "avery@example.test"
    assert len(llm.prompts) == 2
    assert source in llm.prompts[0]
    assert "terminal explicit value" in llm.prompts[0]


def test_incomplete_initial_extraction_retries_once_then_returns_complete_candidate():
    initial = {"user": {"name": "Avery"}}
    corrected = _candidate()
    llm = SequencedLLM([initial, _incomplete("raw_skills"), corrected, _complete()])

    result = LLMExtractor(llm=llm).extract_entities("Avery\nTool-Alpha", sections={})

    assert result["raw_skills"][0]["name"] == "Tool-Alpha"
    assert len(llm.prompts) == 4
    assert '["raw_skills"]' in llm.prompts[2]


def test_fidelity_findings_are_included_in_the_corrective_retry():
    initial = {
        "experiences": [{
            "job_title": "Builder",
            "company_name": "Origin Ltd, Example City",
            "start_date": "2021-06-30",
        }],
    }
    corrected = {
        "experiences": [{
            "job_title": "Builder",
            "company_name": "Origin Ltd",
            "start_date": None,
        }],
    }
    llm = SequencedLLM([
        initial,
        {
            "complete": False,
            "missing_paths": [],
            "unsupported_paths": [],
            "fidelity_paths": ["experiences[0].company_name", "experiences[0].start_date"],
        },
        corrected,
        _complete(),
    ])

    result = LLMExtractor(llm=llm).extract_entities("Builder — Origin Ltd, Example City\nJune 2021", sections={})

    assert result["experiences"][0]["company_name"] == "Origin Ltd"
    assert '"experiences[0].company_name"' in llm.prompts[2]
    assert '"experiences[0].start_date"' in llm.prompts[2]


def test_non_clean_validation_logs_paths_and_corrective_retry_findings(caplog):
    llm = SequencedLLM([
        {"user": {"name": "Avery"}},
        {
            "complete": False,
            "missing_paths": ["raw_skills"],
            "unsupported_paths": ["user.email"],
            "fidelity_paths": ["experiences[0].start_date"],
            "finding_reasons": {"experiences[0].start_date": "precision inflation"},
        },
        _candidate(),
        _complete(),
    ])

    with caplog.at_level(logging.WARNING, logger="src.cv_extractor.llm_extractor"):
        LLMExtractor(llm=llm).extract_entities("Avery\nTool-Alpha", sections={})

    messages = [record.getMessage() for record in caplog.records]
    assert any("missing_paths=['raw_skills']" in message for message in messages)
    assert any("unsupported_paths=['user.email']" in message for message in messages)
    assert any("fidelity_paths=['experiences[0].start_date']" in message for message in messages)
    assert any("finding_reasons={'experiences[0].start_date': 'precision inflation'}" in message for message in messages)
    assert any(
        "CV source-fidelity corrective retry findings=['raw_skills', 'user.email', 'experiences[0].start_date']"
        in message
        for message in messages
    )


def test_incomplete_twice_raises_controlled_error_and_never_returns_candidate():
    llm = SequencedLLM([
        {"user": {"name": "Avery"}},
        _incomplete("projects"),
        {"user": {"name": "Avery"}},
        _incomplete("projects"),
    ])

    with pytest.raises(CVExtractionIncompleteError):
        LLMExtractor(llm=llm).extract_entities("Avery\nRecord One", sections={})
    assert len(llm.prompts) == 4


def test_legitimately_sparse_source_can_be_coverage_complete():
    llm = SequencedLLM([{"user": {"name": "Avery"}}, _complete()])

    result = LLMExtractor(llm=llm).extract_entities("Avery", sections={})

    assert result["user"]["name"] == "Avery"
    assert result["projects"] == []
    assert len(llm.prompts) == 2


def test_unsupported_value_cannot_be_accepted_even_if_validator_marks_complete():
    unsupported = {"complete": True, "missing_paths": [], "unsupported_paths": ["user.email"]}
    llm = SequencedLLM([_candidate(), unsupported, _candidate(), unsupported])

    with pytest.raises(CVExtractionIncompleteError):
        LLMExtractor(llm=llm).extract_entities("Avery", sections={})


@pytest.mark.parametrize(
    ("responses", "available"),
    [([RuntimeError("provider unavailable")], True), ([], False), (["not valid JSON"], True)],
)
def test_provider_or_structured_extraction_failure_is_controlled(responses, available):
    llm = SequencedLLM(responses, available=available)

    with pytest.raises(CVExtractionError):
        LLMExtractor(llm=llm).extract_entities("Avery", sections={})


def test_coverage_validator_failure_is_controlled_and_does_not_accept_candidate():
    llm = SequencedLLM([_candidate(), RuntimeError("validator unavailable")])

    with pytest.raises(CVExtractionError):
        LLMExtractor(llm=llm).extract_entities("Avery", sections={})


def test_candidate_contract_stays_canonical_and_metadata_is_request_local():
    llm = SequencedLLM([_candidate(), _complete()])
    pipeline = CVExtractionPipeline(extractor=LLMExtractor(llm=llm))

    candidate, metadata = pipeline.extract_from_text_with_metadata("Avery\nTool-Alpha")

    assert metadata.extraction_mode == "llm"
    assert set(candidate.model_dump()) == {
        "candidate_id", "user", "candidate_profile", "educations", "experiences",
        "projects", "certificates", "languages", "candidate_skills", "target_roles", "preferences",
    }


def test_concurrent_requests_do_not_share_retry_or_validation_state():
    def run(name: str):
        llm = SequencedLLM([{"user": {"name": name}}, _complete()])
        return LLMExtractor(llm=llm).extract_entities(name, sections={})["user"]["name"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ["One", "Two"]))
    assert results == ["One", "Two"]
