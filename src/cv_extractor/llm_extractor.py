from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.core.llm import get_llm, parse_json_response
from src.models import CVExtractionSchema

logger = logging.getLogger(__name__)


class CVExtractionError(Exception):
    """Safe, operational failure raised when a CV cannot be reliably extracted."""

    public_message = "CV extraction is temporarily unavailable. Please try again later."
    error_code = "CV_EXTRACTION_FAILED"


class CVExtractionIncompleteError(CVExtractionError):
    """The LLM completed both allowed attempts without faithfully covering the CV."""

    public_message = "The CV could not be extracted reliably. Please try again later."


class CoverageValidationResult(BaseModel):
    """Internal, schema-driven source-fidelity assessment of one extraction attempt."""

    complete: bool
    missing_paths: list[str] = Field(default_factory=list)
    unsupported_paths: list[str] = Field(default_factory=list)
    fidelity_paths: list[str] = Field(default_factory=list)
    finding_reasons: dict[str, str] = Field(default_factory=dict)

    @staticmethod
    def _canonicalize_path(path: str) -> str:
        """Normalize generic dotted list indices without interpreting the field name."""
        return re.sub(r"(?<=\w)\.(\d+)(?=\.|$)", r"[\1]", path)

    @model_validator(mode="after")
    def canonicalize_paths(self) -> CoverageValidationResult:
        self.missing_paths = [self._canonicalize_path(path) for path in self.missing_paths]
        self.unsupported_paths = [self._canonicalize_path(path) for path in self.unsupported_paths]
        self.fidelity_paths = [self._canonicalize_path(path) for path in self.fidelity_paths]
        self.finding_reasons = {
            self._canonicalize_path(path): reason
            for path, reason in self.finding_reasons.items()
        }
        return self


class ExtractionResult(dict):
    """Request-local extraction result; operational metadata never enters Candidate."""

    def __init__(self, entities: dict[str, Any], extraction_mode: str = "llm"):
        super().__init__(entities)
        self.extraction_mode = extraction_mode

    @property
    def entities(self) -> dict[str, Any]:
        return dict(self)


class LLMExtractor:
    """Extract CV entities through the centralized, environment-configured LLM only."""

    EXTRACTION_SYSTEM_PROMPT = """You extract a structured candidate profile from source CV text.
Use only explicit source evidence. Populate every schema field and repeated record that
the source supports; leave a field null or empty only when the source does not support it.
Preserve explicit values faithfully, do not infer or fabricate facts, and return only JSON
matching the supplied schema.

Date precision is strict: populate a YYYY-MM-DD field only when the source explicitly
states that exact day-level date. A month/year or year-only value must be null; never invent
a day, month boundary, or date component. A current-status boolean may still reflect explicit
current/ongoing language (true) or an explicitly ended range (false) even when dates are null.

Keep each value in its semantically matching schema field. In particular, an employer name
contains only the organization name; do not append workplace location or address when the
schema provides no field for it. Extract explicit preferences into preferences, but never
infer preferences from other CV facts. When a source explicitly associates a proficiency
qualifier with a skill and raw_skills can represent it, preserve that qualifier; otherwise
leave raw_skills proficiency null."""

    COVERAGE_SYSTEM_PROMPT = """You perform a source-fidelity validation of a structured CV extraction
against the supplied source and extraction schema. Evaluate only information the schema can
represent. Do not invent facts, rewrite the extraction, or require source details that have no
valid schema field.

Report every explicit source-supported omission in missing_paths. Report every value absent
from or contradicted by the source in unsupported_paths. Report materially altered explicit
values, incorrect semantic field placement, and date-precision inflation in fidelity_paths.
A YYYY-MM-DD value is precision inflation unless the source explicitly supplies its day-level
date; a month/year or year-only source date must correspond to null. An employer-name field
must not contain a workplace location or address when the schema has no experience-location
field. Explicit preferences and skill proficiency qualifiers must be preserved when their
schema fields support them.

Only report a missing path when the source explicitly contains schema-representable information
sufficient to populate that path and the extraction omitted it. A nullable field with no such
source-supported value is correctly null, not missing. A collection with no source-supported
records is correctly empty, not missing. Apply these rules generically to every nullable field
and collection. Use bracket list-index paths consistently, for example records[0].field.
For every reported path, include a concise category reason in finding_reasons without quoting
source text or candidate values.

Mark complete true only when all three path lists are empty. Return only JSON matching the
supplied validation-result schema."""

    def __init__(self, llm: Any = None):
        # Injection is for tests; production construction always resolves get_llm().
        self.llm = llm

    def _get_active_llm(self) -> Any:
        if self.llm is not None:
            if hasattr(self.llm, "is_available") and not self.llm.is_available():
                raise CVExtractionError("Injected LLM is unavailable")
            return self.llm
        try:
            return get_llm()
        except Exception as exc:
            logger.warning("Centralized LLM initialization failed: %s", type(exc).__name__)
            raise CVExtractionError("Centralized LLM initialization failed") from exc

    @staticmethod
    def _schema_contract(schema: type[BaseModel]) -> str:
        """Use Pydantic's existing schema as the only extraction-field contract."""
        return json.dumps(schema.model_json_schema(), separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _normalise_json_result(result: Any) -> dict[str, Any]:
        if isinstance(result, BaseModel):
            result = result.model_dump()
        elif isinstance(result, str):
            result = parse_json_response(result)
        if not isinstance(result, dict):
            raise ValueError(f"Expected a JSON object, got {type(result).__name__}")
        return result

    def _invoke_json(self, active_llm: Any, prompt: str, system_prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
        """Invoke the one configured LLM with structured output when the runtime supports it."""
        if hasattr(active_llm, "generate_json"):
            return self._normalise_json_result(
                active_llm.generate_json(prompt=prompt, system_prompt=system_prompt)
            )

        messages = [("system", system_prompt), ("user", prompt)]
        if hasattr(active_llm, "with_structured_output"):
            structured_llm = active_llm.with_structured_output(schema)
            return self._normalise_json_result(structured_llm.invoke(messages))

        raise ValueError("The centralized LLM runtime does not support structured output")

    @staticmethod
    def _population_summary(model: CVExtractionSchema) -> tuple[int, dict[str, int]]:
        """Log shape metadata without logging CV contents or candidate values."""
        dumped = model.model_dump()
        collection_sizes = {
            key: len(value)
            for key, value in dumped.items()
            if isinstance(value, list)
        }

        def scalar_count(value: Any) -> int:
            if isinstance(value, dict):
                return sum(scalar_count(item) for item in value.values())
            if isinstance(value, list):
                return sum(scalar_count(item) for item in value)
            return int(value is not None and value != "")

        return scalar_count(dumped), collection_sizes

    def _extract_once(
        self,
        active_llm: Any,
        source_text: str,
        corrective_paths: list[str] | None = None,
    ) -> CVExtractionSchema:
        schema_contract = self._schema_contract(CVExtractionSchema)
        corrective_instruction = ""
        if corrective_paths is not None:
            corrective_instruction = (
                "\nA prior extraction failed source-fidelity validation. Re-extract the source carefully. "
                "The following schema paths may need attention, but source evidence remains the only truth:\n"
                + json.dumps(corrective_paths, ensure_ascii=False)
            )
        prompt = (
            "SOURCE CV (normalized, complete):\n"
            f"{source_text}\n\n"
            "EXTRACTION SCHEMA (JSON Schema):\n"
            f"{schema_contract}"
            f"{corrective_instruction}"
        )
        logger.info("CV source chars=%d CV extraction prompt chars=%d", len(source_text), len(prompt))
        try:
            raw_result = self._invoke_json(active_llm, prompt, self.EXTRACTION_SYSTEM_PROMPT, CVExtractionSchema)
            model = CVExtractionSchema.model_validate(raw_result)
        except Exception as exc:
            logger.warning("Centralized LLM extraction failed: %s", type(exc).__name__)
            raise CVExtractionError("Centralized LLM extraction failed") from exc

        scalar_count, collection_sizes = self._population_summary(model)
        logger.info(
            "CV structured extraction populated scalar fields=%d collection sizes=%s",
            scalar_count,
            collection_sizes,
        )
        return model

    def _validate_coverage(
        self,
        active_llm: Any,
        source_text: str,
        extraction: CVExtractionSchema,
    ) -> CoverageValidationResult:
        schema_contract = self._schema_contract(CVExtractionSchema)
        result_contract = self._schema_contract(CoverageValidationResult)
        prompt = (
            "SOURCE CV (normalized, complete):\n"
            f"{source_text}\n\n"
            "EXTRACTION SCHEMA (JSON Schema):\n"
            f"{schema_contract}\n\n"
            "STRUCTURED EXTRACTION (JSON):\n"
            f"{json.dumps(extraction.model_dump(), separators=(',', ':'), ensure_ascii=False)}\n\n"
            "VALIDATION RESULT SCHEMA (JSON Schema):\n"
            f"{result_contract}"
        )
        logger.info("CV source chars=%d CV coverage prompt chars=%d", len(source_text), len(prompt))
        try:
            raw_result = self._invoke_json(
                active_llm,
                prompt,
                self.COVERAGE_SYSTEM_PROMPT,
                CoverageValidationResult,
            )
            validation = CoverageValidationResult.model_validate(raw_result)
        except Exception as exc:
            logger.warning("Centralized LLM coverage validation failed: %s", type(exc).__name__)
            raise CVExtractionError("Centralized LLM coverage validation failed") from exc

        logger.info(
            "CV source-fidelity validation complete=%s missing_paths=%d unsupported_paths=%d fidelity_paths=%d",
            validation.complete,
            len(validation.missing_paths),
            len(validation.unsupported_paths),
            len(validation.fidelity_paths),
        )
        if not self._is_faithful(validation):
            logger.warning(
                "CV source-fidelity findings complete=%s missing_paths=%s unsupported_paths=%s fidelity_paths=%s finding_reasons=%s",
                validation.complete,
                validation.missing_paths,
                validation.unsupported_paths,
                validation.fidelity_paths,
                validation.finding_reasons,
            )
        return validation

    def extract_entities(
        self,
        full_text: str,
        sections: dict[str, str] | None = None,
        document_urls: list[str] | None = None,
    ) -> ExtractionResult:
        """Extract, validate coverage, then make exactly one corrective LLM retry if needed."""
        del sections, document_urls  # Semantic interpretation belongs to the LLM; state is request-local.
        if not full_text or not full_text.strip():
            raise ValueError("CV text cannot be empty")

        active_llm = self._get_active_llm()
        first = self._extract_once(active_llm, full_text)
        first_validation = self._validate_coverage(active_llm, full_text, first)
        if self._is_faithful(first_validation):
            logger.info("Successfully extracted, schema-validated, and coverage-validated CV entities using centralized LLM service.")
            return ExtractionResult(first.model_dump())

        corrective_paths = self._corrective_paths(first_validation)
        corrective_reasons = {
            path: validation_reason
            for path, validation_reason in first_validation.finding_reasons.items()
            if path in corrective_paths
        }
        logger.warning(
            "CV source-fidelity corrective retry findings=%s finding_reasons=%s",
            corrective_paths,
            corrective_reasons,
        )
        retry = self._extract_once(active_llm, full_text, corrective_paths)
        retry_validation = self._validate_coverage(active_llm, full_text, retry)
        if self._is_faithful(retry_validation):
            logger.info("Successfully extracted CV entities after one coverage-corrective centralized LLM retry.")
            return ExtractionResult(retry.model_dump())

        logger.warning(
            "CV extraction remained unfaithful after its single corrective retry: missing_paths=%d unsupported_paths=%d fidelity_paths=%d",
            len(retry_validation.missing_paths),
            len(retry_validation.unsupported_paths),
            len(retry_validation.fidelity_paths),
        )
        raise CVExtractionIncompleteError("Coverage validation remained incomplete")

    @staticmethod
    def _is_faithful(validation: CoverageValidationResult) -> bool:
        return (
            validation.complete
            and not validation.missing_paths
            and not validation.unsupported_paths
            and not validation.fidelity_paths
        )

    @staticmethod
    def _corrective_paths(validation: CoverageValidationResult) -> list[str]:
        """Return every validator finding once, without interpreting its domain meaning."""
        return list(dict.fromkeys(
            validation.missing_paths
            + validation.unsupported_paths
            + validation.fidelity_paths
        ))
