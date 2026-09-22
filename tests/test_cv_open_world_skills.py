from __future__ import annotations

from src.cv_extractor.llm_extractor import LLMExtractor
from src.cv_extractor.pipeline import CVExtractionPipeline


class MockLLM:
    def __init__(self, responses: list[dict]):
        self.responses = iter(responses)

    def is_available(self) -> bool:
        return True

    def generate_json(self, prompt: str, system_prompt: str):
        return next(self.responses)


def test_known_and_explicit_unknown_skills_preserve_existing_taxonomy_behavior():
    source = "Avery\nPython, Tool-Alpha"
    llm = MockLLM([
        {"user": {"name": "Avery"}, "raw_skills": [{"name": "Python"}, {"name": "Tool-Alpha"}]},
        {"complete": True, "missing_paths": [], "unsupported_paths": []},
    ])
    candidate = CVExtractionPipeline(extractor=LLMExtractor(llm=llm)).extract_from_text(source)

    skills = {item.name: item for item in candidate.candidate_skills}
    assert skills["Python"].skill_id == "skill_python"
    assert skills["Tool-Alpha"].skill_id is None
    assert all(item.evidence for item in skills.values())


def test_punctuation_heavy_explicit_skill_retains_evidence_and_no_inferred_proficiency():
    source = "Avery\nC++"
    llm = MockLLM([
        {"user": {"name": "Avery"}, "raw_skills": [{"name": "C++", "proficiency": None}]},
        {"complete": True, "missing_paths": [], "unsupported_paths": []},
    ])
    candidate = CVExtractionPipeline(extractor=LLMExtractor(llm=llm)).extract_from_text(source)

    skill = next(item for item in candidate.candidate_skills if item.name == "C++")
    assert skill.proficiency is None
    assert skill.evidence
