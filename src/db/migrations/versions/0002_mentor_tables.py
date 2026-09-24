"""Add mentor conversations and messages tables

Revision ID: 0002_mentor_tables
Revises: 0001_initial_ai_persistence
Create Date: 2026-09-22 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_mentor_tables"
down_revision: Union[str, None] = "0001_initial_ai_persistence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mentor_conversations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("active_agent", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_mentor_conversations_user_id", "mentor_conversations", ["user_id"])

    op.create_table(
        "mentor_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_mentor_messages_conversation_id", "mentor_messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("mentor_messages")
    op.drop_table("mentor_conversations")
