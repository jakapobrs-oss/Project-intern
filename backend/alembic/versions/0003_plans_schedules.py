"""plans + schedules

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plans_name", "plans", ["name"])

    op.create_table(
        "plan_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("presentation_id", sa.Uuid(), sa.ForeignKey("presentations.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_sec_override", sa.Integer(), nullable=True),
    )
    op.create_index("ix_plan_items_plan_id", "plan_items", ["plan_id"])

    op.create_table(
        "schedules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("player_group_id", sa.Uuid(), sa.ForeignKey("player_groups.id"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("repeat_rule", sa.String(512), nullable=True),
        sa.Column("daily_window_start", sa.String(8), nullable=True),
        sa.Column("daily_window_end", sa.String(8), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_schedules_name", "schedules", ["name"])
    op.create_index("ix_schedules_plan_id", "schedules", ["plan_id"])
    op.create_index("ix_schedules_player_group_id", "schedules", ["player_group_id"])
    op.create_index("ix_schedules_start_at", "schedules", ["start_at"])
    op.create_index("ix_schedules_end_at", "schedules", ["end_at"])
    op.create_index("ix_schedules_priority", "schedules", ["priority"])
    op.create_index("ix_schedules_status", "schedules", ["status"])


def downgrade() -> None:
    op.drop_table("schedules")
    op.drop_table("plan_items")
    op.drop_table("plans")
