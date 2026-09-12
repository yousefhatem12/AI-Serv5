"""
SQLAlchemy ORM model for persisting job requirement profiles.

Maps to the *existing* ``jobs`` table using ``extend_existing=True`` to avoid
redefining it; only the AI-contract columns are declared here.

Columns declared here mirror the BACKEND_SCHEMA.md contract:
  - canonical_role        VARCHAR(150)
  - min_years_experience  INT
  - max_years_experience  INT
  - responsibilities      JSON
  - structured_profile    JSON   (full JobRequirementProfile blob)
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.sqlite import JSON  # falls back gracefully on PostgreSQL

from src.db.base import Base


class JobRequirementModel(Base):
    """
    Extends the backend ``jobs`` table with AI-extracted requirement fields.

    ``extend_existing=True`` ensures this model co-exists with any other
    SQLAlchemy model already mapped to the same table (e.g. the backend ORM).
    """

    __tablename__ = "jobs"
    __table_args__ = {"extend_existing": True}

    # Primary key — mirrors the backend jobs.id column (UUID stored as string)
    id = Column(String, primary_key=True)

    # ── AI-contract columns (added via BACKEND_SCHEMA.md migration) ───
    canonical_role = Column(String(150), nullable=True)
    min_years_experience = Column(Integer, nullable=True)
    max_years_experience = Column(Integer, nullable=True)
    responsibilities = Column(JSON, nullable=True)

    # Full structured profile blob for downstream consumers (search, matching)
    structured_profile = Column(JSON, nullable=True)
