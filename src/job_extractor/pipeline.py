"""
3-step Job Description Understanding pipeline orchestrator.

Step 1 — Extract:    LLM extracts a raw structured profile from the JD text.
Step 2 — Normalize:  TaxonomyManager resolves skill aliases to canonical IDs.
Step 3 — Score:      Heuristic confidence score based on extraction completeness.
"""

import logging

from src.core.llm_service import LLMService, get_llm_service
from src.taxonomy.taxonomy_manager import TaxonomyManager

from .llm_extractor import JobLLMExtractor
from .models import JobRequirementProfile
from .skill_normalizer import normalize_skills

logger = logging.getLogger(__name__)


class JobExtractionPipeline:
    """
    Orchestrates the full job description understanding pipeline.

    Designed to be instantiated once per application lifecycle (singleton via DI)
    and reused across requests — all internal components are stateless per call.
    """

    def __init__(
        self,
        taxonomy_manager: TaxonomyManager | None = None,
        llm_service: LLMService | None = None,
    ):
        self.taxonomy = taxonomy_manager or TaxonomyManager()
        self.extractor = JobLLMExtractor(llm_service=llm_service or get_llm_service())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, job_description: str) -> JobRequirementProfile:
        """
        Run the full 3-step pipeline on raw job description text.

        Args:
            job_description: The raw text of the job posting.

        Returns:
            A validated JobRequirementProfile.

        Raises:
            ValueError: Propagated from JobLLMExtractor when LLM is
                        unavailable or returns an un-parsable response.
        """
        logger.info("Starting job description extraction pipeline")

        # ── Step 1: LLM extraction ──────────────────────────────────────
        raw = self.extractor.extract(job_description)
        logger.debug("Step 1 complete — raw extraction done")

        # ── Step 2: Skill normalization ─────────────────────────────────
        required_skills = normalize_skills(
            raw.get("required_skills", []), self.taxonomy
        )
        preferred_skills = normalize_skills(
            raw.get("preferred_skills", []), self.taxonomy
        )
        logger.debug(
            "Step 2 complete — %d required, %d preferred skills normalized",
            len(required_skills),
            len(preferred_skills),
        )

        # ── Step 3: Confidence scoring ──────────────────────────────────
        confidence = _score_confidence(
            role_family=raw.get("role_family"),
            required_skills_count=len(required_skills),
            responsibilities=raw.get("responsibilities", []),
        )
        logger.debug("Step 3 complete — extraction_confidence=%.2f", confidence)

        profile = JobRequirementProfile(
            role_family=raw.get("role_family"),
            seniority=raw.get("seniority"),
            canonical_role=raw.get("canonical_role"),
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            responsibilities=raw.get("responsibilities", []),
            min_years_experience=raw.get("min_years_experience"),
            max_years_experience=raw.get("max_years_experience"),
            constraints=raw.get("constraints", []),
            extraction_confidence=confidence,
        )

        logger.info(
            "Job extraction pipeline complete — confidence=%.2f, "
            "required_skills=%d, preferred_skills=%d",
            profile.extraction_confidence,
            len(profile.required_skills),
            len(profile.preferred_skills),
        )
        return profile


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _score_confidence(
    role_family: str | None,
    required_skills_count: int,
    responsibilities: list[str],
) -> float:
    """
    Simple heuristic confidence score (0.0 – 1.0).

    Starts at 0.90 and applies deductions for signals of low-quality extraction:
      -0.10  role_family could not be determined
      -0.10  fewer than 3 required skills extracted
      -0.05  no responsibilities extracted
    """
    score = 0.90
    if role_family is None:
        score -= 0.10
    if required_skills_count < 3:
        score -= 0.10
    if not responsibilities:
        score -= 0.05
    return round(max(0.0, score), 2)
