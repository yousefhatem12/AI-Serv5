from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.dependencies import get_cv_pipeline
from src.api.main import app
from src.cv_extractor.llm_extractor import LLMExtractor
from src.cv_extractor.pipeline import CVExtractionPipeline


class MockLLM:
    def __init__(self, responses: list[object], available: bool = True):
        self.responses = iter(responses)
        self.available = available

    def is_available(self) -> bool:
        return self.available

    def generate_json(self, prompt: str, system_prompt: str):
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def _pipeline(responses: list[object], available: bool = True) -> CVExtractionPipeline:
    return CVExtractionPipeline(extractor=LLMExtractor(llm=MockLLM(responses, available)))


def test_successful_text_extraction_is_llm_only_and_keeps_canonical_response():
    app.dependency_overrides[get_cv_pipeline] = lambda: _pipeline([
        {"user": {"name": "Avery", "email": "avery@example.test"}, "raw_skills": [{"name": "Tool-Alpha"}]},
        {"complete": True, "missing_paths": [], "unsupported_paths": []},
    ])
    try:
        response = TestClient(app).post("/api/v1/cv/extract-text", json={"text": "Avery\nTool-Alpha"})
        assert response.status_code == 200
        assert response.headers["X-CV-Extraction-Mode"] == "llm"
        assert "X-CV-Fallback-Reason" not in response.headers
        assert set(response.json()) == {
            "candidate_id", "user", "candidate_profile", "educations", "experiences",
            "projects", "certificates", "languages", "candidate_skills", "target_roles", "preferences",
        }
    finally:
        app.dependency_overrides.pop(get_cv_pipeline, None)


def test_provider_failure_is_a_safe_service_error_without_heuristic_candidate():
    app.dependency_overrides[get_cv_pipeline] = lambda: _pipeline([RuntimeError("secret=do-not-expose")])
    try:
        response = TestClient(app).post("/api/v1/cv/extract-text", json={"text": "Avery"})
        assert response.status_code == 503
        assert response.json()["error_code"] == "CV_EXTRACTION_FAILED"
        assert "secret" not in str(response.json()).lower()
        assert "X-CV-Extraction-Mode" not in response.headers
    finally:
        app.dependency_overrides.pop(get_cv_pipeline, None)


def test_file_endpoint_validates_input_before_calling_the_llm():
    client = TestClient(app)

    unsupported = client.post(
        "/api/v1/cv/extract-file",
        files={"file": ("candidate.bin", b"content", "application/octet-stream")},
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"

    empty = client.post(
        "/api/v1/cv/extract-file",
        files={"file": ("candidate.txt", b"", "text/plain")},
    )
    assert empty.status_code == 400
    assert empty.json()["error_code"] == "EMPTY_FILE"


def test_file_endpoint_uses_the_same_llm_only_pipeline_and_preserves_candidate_id():
    app.dependency_overrides[get_cv_pipeline] = lambda: _pipeline([
        {"user": {"name": "Avery"}, "raw_skills": [{"name": "Tool-Alpha"}]},
        {"complete": True, "missing_paths": [], "unsupported_paths": []},
    ])
    try:
        response = TestClient(app).post(
            "/api/v1/cv/extract-file",
            files={"file": ("..\\candidate.txt", b"Avery\nTool-Alpha", "text/plain")},
            data={"candidate_id": "cand_file"},
        )
        assert response.status_code == 200
        assert response.json()["candidate_id"] == "cand_file"
        assert response.headers["X-CV-Extraction-Mode"] == "llm"
    finally:
        app.dependency_overrides.pop(get_cv_pipeline, None)
