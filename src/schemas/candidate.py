from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

# Canonical Candidate Schemas directly aligned with backend schema
from src.models.candidate import (
    Candidate,
    CandidatePreferences,
    CandidateProfile,
    CandidateProfileDetails,
    CandidateSkill,
    CertificateItem,
    CertificationItem,
    EducationItem,
    EvidenceItem,
    ExperienceItem,
    LanguageItem,
    ProjectItem,
    RawSkillItem,
    UserProfile,
    normalize_backend_date,
)

# Baseline aliases
Education = EducationItem
preferences = CandidatePreferences
SkillEvidence = EvidenceItem
ExtractedCandiateSkill = CandidateSkill

__all__ = [
    "Candidate",
    "CandidatePreferences",
    "CandidateProfile",
    "CandidateProfileDetails",
    "CandidateSkill",
    "CertificateItem",
    "CertificationItem",
    "Education",
    "EducationItem",
    "EvidenceItem",
    "ExperienceItem",
    "ExtractedCandiateSkill",
    "LanguageItem",
    "ProjectItem",
    "RawSkillItem",
    "UserProfile",
    "normalize_backend_date",
    "preferences",
    "SkillEvidence",
]
