"""playback_logs (§28 reporting)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-05
"""
from typing import Union
from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playback_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_id", sa.Uuid(), sa.ForeignKey("contents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("presentation_id", sa.Uuid(), nullable=True),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_playback_logs_device_id", "playback_logs", ["device_id"])
    op.create_index("ix_playback_logs_content_id", "playback_logs", ["content_id"])
    op.create_index("ix_playback_logs_played_at", "playback_logs", ["played_at"])


def downgrade() -> None:
    op.drop_index("ix_playback_logs_played_at", table_name="playback_logs")
    op.drop_index("ix_playback_logs_content_id", table_name="playback_logs")
    op.drop_index("ix_playback_logs_device_id", table_name="playback_logs")
    op.drop_table("playback_logs")
