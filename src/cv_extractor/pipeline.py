from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models.candidate import (
    Candidate,
    CandidatePreferences,
    CandidateProfile,
    CandidateSkill,
    CertificateItem,
    EducationItem,
    ExperienceItem,
    LanguageItem,
    ProjectItem,
    UserProfile,
)
from ..taxonomy.taxonomy_manager import (
    LEGITIMATE_EXPLICIT_SKILLS,
    STOPWORDS_BLACKLIST,
    TaxonomyManager,
)
from ..utils.text_cleaner import TextCleaner
from .confidence_scorer import ConfidenceScorer
from .document_loader import DocumentLoader
from .evidence_linker import EvidenceLinker
from .link_associator import ProjectLinkAssociator
from .llm_extractor import LLMExtractor

logger = logging.getLogger(__name__)


@dataclass
class CVExtractionMetadata:
    """
    Internal request-local CV extraction execution metadata.
    Kept strictly separate from Candidate domain models.
    """
    extraction_mode: str = "llm"


class CVExtractionPipeline:
    """
    End-to-end CV Profile Extraction Pipeline.
    Strict LLM extraction flow with Hybrid Open-World Taxonomy:
      1. Extract raw text from document (PDF / DOCX / TXT).
      2. Clean & segment text into structured sections.
      3. Centralized LLM extracts and coverage-validates candidate entities.
      4. Detect all skill mentions & map them to canonical skills.
      5. Associate GitHub and portfolio URLs to projects using strict evidence rules.
      6. Calculate confidence score for each skill using multi-factor signals.
      7. Link verifiable textual evidence snippet for each extracted skill.
      8. Normalize dates, employment types, languages, and profile contact details.
      9. Output validated, backend-ready Candidate profile.
    """

    def __init__(
        self,
        taxonomy_manager: TaxonomyManager | None = None,
        document_loader: DocumentLoader | None = None,
        extractor: LLMExtractor | None = None,
        llm_extractor: LLMExtractor | None = None,
    ):
        if taxonomy_manager is not None:
            self.taxonomy = taxonomy_manager
        else:
            try:
                self.taxonomy = TaxonomyManager()
            except Exception as e:
                logger.warning(f"Failed to initialize TaxonomyManager: {e}. Degrading gracefully without taxonomy.")
                self.taxonomy = None
        self.loader = document_loader or DocumentLoader()
        self.extractor = extractor or llm_extractor or LLMExtractor()

    def extract_from_file(
        self,
        file_path: str,
        candidate_id: str | None = None,
        return_metadata: bool = False,
    ) -> Candidate | tuple[Candidate, CVExtractionMetadata]:
        """
        Executes full extraction pipeline on a CV file path.
        """
        raw_text, doc_format, document_urls = self.loader.load_text(file_path)
        if not raw_text.strip():
            raise ValueError(f"Could not extract any readable text from document: {file_path}")

        return self.extract_from_text(
            raw_text=raw_text,
            file_name=Path(file_path).name,
            candidate_id=candidate_id or f"cand_{uuid.uuid4().hex[:8]}",
            document_urls=document_urls,
            return_metadata=return_metadata,
        )

    def extract_from_file_with_metadata(
        self,
        file_path: str,
        candidate_id: str | None = None,
    ) -> tuple[Candidate, CVExtractionMetadata]:
        """
        Executes file extraction returning (Candidate, CVExtractionMetadata).
        """
        return self.extract_from_file(
            file_path=file_path,
            candidate_id=candidate_id,
            return_metadata=True,
        )

    def extract_from_text(
        self,
        raw_text: str,
        file_name: str | None = None,
        candidate_id: str | None = None,
        document_urls: list[str] | None = None,
        return_metadata: bool = False,
    ) -> Candidate | tuple[Candidate, CVExtractionMetadata]:
        """
        Executes strict 9-step pipeline on raw text.
        """
        cid = candidate_id or f"cand_{uuid.uuid4().hex[:8]}"
        doc_urls = document_urls if document_urls is not None else []

        # Step 1 & 2: Clean text and segment sections
        cleaned_text = TextCleaner.clean_text(raw_text)
        sections = TextCleaner.segment_sections(cleaned_text)

        # Step 3: centralized LLM extraction and generic coverage validation
        entities = self.extractor.extract_entities(cleaned_text, sections, document_urls=doc_urls)
        metadata = CVExtractionMetadata(extraction_mode="llm")

        # Apply strict 7-rule project-to-link association
        if "projects" in entities and isinstance(entities["projects"], list):
            ProjectLinkAssociator.associate_projects_with_links(
                projects=entities["projects"],
                full_text=cleaned_text,
                document_urls=doc_urls
            )

        # Step 4: Collect candidate skill mentions and raw proficiency levels
        skill_candidates: list[str] = []
        raw_skill_levels: dict[str, str] = {}

        # A) Explicit skills from extractor
        for s in (entities.get("raw_skills") or []):
            skill_name = None
            skill_level = None
            if hasattr(s, "name"):
                skill_name = s.name
                skill_level = getattr(s, "level", None) or getattr(s, "proficiency", None)
            elif isinstance(s, dict):
                skill_name = s.get("name")
                skill_level = s.get("level") or s.get("proficiency") or s.get("proficiency_level") or s.get("raw_level")
            elif isinstance(s, str) and s.strip():
                skill_name = s.strip()

            if skill_name and isinstance(skill_name, str) and skill_name.strip():
                clean_name = skill_name.strip()
                skill_candidates.append(clean_name)
                if skill_level and isinstance(skill_level, str) and skill_level.strip():
                    raw_skill_levels[clean_name.lower()] = skill_level.strip()

        # B) Technologies mentioned in experiences
        for exp in (entities.get("experiences") or entities.get("experience") or []):
            if isinstance(exp, dict):
                for tech in (exp.get("technologies") or []):
                    if isinstance(tech, str) and tech.strip():
                        skill_candidates.append(tech.strip())

        # C) Technologies mentioned in projects
        for proj in (entities.get("projects") or []):
            if isinstance(proj, dict):
                for tech in (proj.get("technologies") or []):
                    if isinstance(tech, str) and tech.strip():
                        skill_candidates.append(tech.strip())


        # Step 5, 6, 7, 8: Non-destructive Taxonomy Resolution, Deduplication, Evidence Linking & Scoring
        resolved_skills_map: dict[str, dict[str, Any]] = {}

        for raw_mention in skill_candidates:
            if not raw_mention or len(raw_mention.strip()) < 2:
                continue

            clean_mention = TaxonomyManager.clean_skill_label(raw_mention)
            if not clean_mention or len(clean_mention) < 2:
                continue

            if self.taxonomy and self.taxonomy.is_blacklisted(clean_mention, is_explicit=True):
                continue
            elif clean_mention.lower() in STOPWORDS_BLACKLIST and clean_mention.lower() not in LEGITIMATE_EXPLICIT_SKILLS:
                continue

            # Candidate name and email must never be extracted as skills
            cand_name = entities.get("name") or (entities.get("user") or {}).get("name")
            cand_email = entities.get("email") or (entities.get("user") or {}).get("email")
            if cand_name and clean_mention.lower() == cand_name.strip().lower():
                continue
            if cand_email and clean_mention.lower() == cand_email.strip().lower():
                continue

            # Non-destructive taxonomy resolution:
            # KNOWN -> (canonical skill_id, canonical name)
            # UNKNOWN -> (None, cleaned original name)
            if self.taxonomy:
                skill_id, canonical_name = self.taxonomy.resolve(clean_mention)
            else:
                skill_id, canonical_name = None, clean_mention

            if not canonical_name:
                continue

            # Deduplication key:
            # Known: dedup by canonical skill_id
            # Unknown: dedup by normalized lowercase name
            if skill_id is not None:
                dedup_key = f"id:{skill_id}"
            else:
                dedup_key = f"name:{canonical_name.strip().lower()}"

            cand_level = (
                raw_skill_levels.get(clean_mention.lower().strip())
                or (self.taxonomy and raw_skill_levels.get(TaxonomyManager._clean_string(clean_mention)))
                or raw_skill_levels.get(canonical_name.lower().strip())
                or (self.taxonomy and raw_skill_levels.get(TaxonomyManager._clean_string(canonical_name)))
                or (skill_id and raw_skill_levels.get(skill_id))
                or ""
            )

            if dedup_key not in resolved_skills_map:
                resolved_skills_map[dedup_key] = {
                    "skill_id": skill_id,
                    "name": canonical_name,
                    "raw_level": cand_level,
                    "mentions": [clean_mention],
                }
            else:
                resolved_skills_map[dedup_key]["mentions"].append(clean_mention)
                if not resolved_skills_map[dedup_key]["raw_level"] and cand_level:
                    resolved_skills_map[dedup_key]["raw_level"] = cand_level

        final_skills: list[CandidateSkill] = []

        for item in resolved_skills_map.values():
            skill_id = item["skill_id"]
            canonical_name = item["name"]
            raw_level = item["raw_level"]
            mentions = item["mentions"]

            taxonomy_item = self.taxonomy.find_skill(canonical_name) if self.taxonomy else None

            # Evidence Verification (Must find verifiable proof in the CV text)
            evidence_items = EvidenceLinker.link_evidence(
                skill_name=canonical_name,
                taxonomy_item=taxonomy_item,
                sections=sections,
                full_text=cleaned_text
            )

            # Fallback search using raw mentions if canonical name didn't catch evidence
            if not evidence_items:
                for m in mentions:
                    evidence_items = EvidenceLinker.link_evidence(
                        skill_name=m,
                        taxonomy_item=None,
                        sections=sections,
                        full_text=cleaned_text
                    )
                    if evidence_items:
                        break

            # If no supporting evidence exists anywhere in the text, reject false positive
            if not evidence_items:
                continue

            # Context-Aware Confidence Calculation (independent of proficiency)
            confidence = ConfidenceScorer.calculate_confidence(evidence_items)

            # Proficiency MUST be explicitly supported by CV mention, never inferred from evidence depth!
            explicit_proficiency = None
            if raw_level and str(raw_level).lower().strip() not in ("", "unknown", "none"):
                lvl_clean = str(raw_level).lower().strip()
                if lvl_clean in ("expert", "advanced", "intermediate", "beginner"):
                    explicit_proficiency = lvl_clean
                elif lvl_clean in ConfidenceScorer.LEVEL_SYNONYMS:
                    explicit_proficiency = ConfidenceScorer.LEVEL_SYNONYMS[lvl_clean].value

            final_skills.append(
                CandidateSkill(
                    skill_id=skill_id,
                    name=canonical_name,
                    proficiency=explicit_proficiency,
                    confidence=confidence,
                    evidence=evidence_items
                )
            )

        # Sort skills by confidence descending
        final_skills.sort(key=lambda s: s.confidence, reverse=True)

        # Step 9: Assemble Validated Candidate Object
        education_items = [EducationItem(**item) if isinstance(item, dict) else item for item in (entities.get("educations") or entities.get("education") or [])]
        experience_items = [ExperienceItem(**item) if isinstance(item, dict) else item for item in (entities.get("experiences") or entities.get("experience") or [])]
        project_items = [ProjectItem(**item) if isinstance(item, dict) else item for item in (entities.get("projects") or [])]
        cert_items = [CertificateItem(**item) if isinstance(item, dict) else item for item in (entities.get("certificates") or entities.get("certifications") or [])]
        language_items = [LanguageItem(**item) if isinstance(item, dict) else item for item in (entities.get("languages") or [])]

        target_roles = entities.get("target_roles") or []

        user_dict = entities.get("user") if isinstance(entities.get("user"), dict) else {}
        user = UserProfile(
            name=user_dict.get("name") or entities.get("name"),
            email=user_dict.get("email") or entities.get("email"),
        )

        cand_prof_dict = entities.get("candidate_profile") if isinstance(entities.get("candidate_profile"), dict) else {}
        candidate_profile = CandidateProfile(
            headline=cand_prof_dict.get("headline") or entities.get("headline"),
            bio=cand_prof_dict.get("bio") or entities.get("bio"),
            phone=cand_prof_dict.get("phone") or entities.get("phone"),
            location=cand_prof_dict.get("location") or entities.get("location"),
            linkedin_url=cand_prof_dict.get("linkedin_url") or entities.get("linkedin_url"),
            github_url=cand_prof_dict.get("github_url") or entities.get("github_url"),
            portfolio_url=cand_prof_dict.get("portfolio_url") or entities.get("portfolio_url"),
        )

        extracted_preferences = entities.get("preferences")
        preferences = (
            extracted_preferences
            if isinstance(extracted_preferences, CandidatePreferences)
            else CandidatePreferences.model_validate(extracted_preferences or {})
        )

        candidate = Candidate(
            candidate_id=cid,
            user=user,
            candidate_profile=candidate_profile,
            educations=education_items,
            experiences=experience_items,
            projects=project_items,
            certificates=cert_items,
            languages=language_items,
            candidate_skills=final_skills,
            target_roles=target_roles,
            preferences=preferences,
        )

        if return_metadata:
            return candidate, metadata
        return candidate

    def extract_from_text_with_metadata(
        self,
        raw_text: str,
        file_name: str | None = None,
        candidate_id: str | None = None,
        document_urls: list[str] | None = None,
    ) -> tuple[Candidate, CVExtractionMetadata]:
        """
        Executes text extraction and returns (Candidate, CVExtractionMetadata).
        """
        return self.extract_from_text(
            raw_text=raw_text,
            file_name=file_name,
            candidate_id=candidate_id,
            document_urls=document_urls,
            return_metadata=True,
        )
