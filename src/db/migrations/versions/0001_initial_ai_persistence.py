"""Initial AI-owned persistence schema

Revision ID: 0001_initial_ai_persistence
Revises: 
Create Date: 2026-09-20 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_ai_persistence"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. jobs table (AI requirement and ingestion persistence)
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=100), primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("company", sa.String(length=300), nullable=True),
        sa.Column("role", sa.String(length=300), nullable=True),
        sa.Column("role_family", sa.String(length=150), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("department", sa.String(length=150), nullable=True),
        sa.Column("location", sa.String(length=300), nullable=True),
        sa.Column("work_mode", sa.String(length=50), nullable=True),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("experience_level", sa.String(length=100), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=True),
        sa.Column("salary", sa.String(length=300), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("source_external_id", sa.String(length=300), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(), nullable=True),
        sa.Column("description_is_partial", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("canonical_role", sa.String(length=150), nullable=True),
        sa.Column("min_years_experience", sa.Integer(), nullable=True),
        sa.Column("max_years_experience", sa.Integer(), nullable=True),
        sa.Column("responsibilities", sa.JSON(), nullable=True),
        sa.Column("structured_profile", sa.JSON(), nullable=True),
    )
    op.create_index("ix_jobs_source", "jobs", ["source"])
    op.create_index("ix_jobs_source_external_id", "jobs", ["source_external_id"])

    # 2. match_records table (Explainable Job Match)
    op.create_table(
        "match_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=100), nullable=False),
        sa.Column("candidate_id", sa.String(length=100), nullable=False),
        sa.Column("overall_match_score", sa.Float(), nullable=False),
        sa.Column("qualification_status", sa.String(length=50), nullable=False),
        sa.Column("full_candidate_summary", sa.Text(), nullable=False),
        sa.Column("skill_breakdown_json", sa.Text(), nullable=False),
        sa.Column("missing_critical_skills_json", sa.Text(), nullable=False),
        sa.Column("recommended_upskilling_path_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_match_records_job_id", "match_records", ["job_id"])
    op.create_index("ix_match_records_candidate_id", "match_records", ["candidate_id"])
    op.create_index("ix_match_records_qualification_status", "match_records", ["qualification_status"])

    # 3. interview_sessions table (Interview Coach)
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=100), nullable=False),
        sa.Column("candidate_id", sa.String(length=100), nullable=False),
        sa.Column("target_role", sa.String(length=150), nullable=False),
        sa.Column("questions_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_interview_sessions_job_id", "interview_sessions", ["job_id"])
    op.create_index("ix_interview_sessions_candidate_id", "interview_sessions", ["candidate_id"])

    # 4. interview_answer_evaluations table (Interview Coach)
    op.create_table(
        "interview_answer_evaluations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("question_id", sa.String(length=100), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("strengths_json", sa.Text(), nullable=False),
        sa.Column("improvements_json", sa.Text(), nullable=False),
        sa.Column("ideal_answer_outline", sa.Text(), nullable=False),
        sa.Column("security_assessment_json", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_interview_answer_evaluations_session_id", "interview_answer_evaluations", ["session_id"])
    op.create_index("ix_interview_answer_evaluations_question_id", "interview_answer_evaluations", ["question_id"])

    # 5. roadmaps table (Career Roadmap)
    op.create_table(
        "roadmaps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("roadmap_id", sa.String(length=100), nullable=False),
        sa.Column("candidate_id", sa.String(length=100), nullable=False),
        sa.Column("target_role", sa.String(length=150), nullable=False),
        sa.Column("role_family", sa.String(length=100), nullable=True),
        sa.Column("total_weeks", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_roadmaps_roadmap_id", "roadmaps", ["roadmap_id"], unique=True)
    op.create_index("ix_roadmaps_candidate_id", "roadmaps", ["candidate_id"])

    # 6. review_queue table (AI Safety / Review Queue)
    op.create_table(
        "review_queue",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("item_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("flagged_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("reviewer_id", sa.String(length=100), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("resolution_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_review_queue_item_type", "review_queue", ["item_type"])
    op.create_index("ix_review_queue_target_id", "review_queue", ["target_id"])
    op.create_index("ix_review_queue_status", "review_queue", ["status"])
    op.create_index("ix_review_queue_priority", "review_queue", ["priority"])

    # 7. skill_resources table (Skill Resources)
    op.create_table(
        "skill_resources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("skill_id", sa.String(length=100), nullable=False),
        sa.Column("video_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("channel_name", sa.String(length=255), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("duration", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending_review"),
        sa.Column("last_refreshed", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_skill_resources_skill_id", "skill_resources", ["skill_id"])
    op.create_index("ix_skill_resources_video_id", "skill_resources", ["video_id"], unique=True)


def downgrade() -> None:
    op.drop_table("skill_resources")
    op.drop_table("review_queue")
    op.drop_table("roadmaps")
    op.drop_table("interview_answer_evaluations")
    op.drop_table("interview_sessions")
    op.drop_table("match_records")
    op.drop_table("jobs")
