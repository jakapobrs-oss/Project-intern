"""devices + contents + presentations

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===== player_groups =====
    op.create_table(
        "player_groups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_player_groups_name", "player_groups", ["name"])

    # ===== devices =====
    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("location", sa.String(255), nullable=False, server_default=""),
        sa.Column("pairing_code", sa.String(16), nullable=True, unique=True),
        sa.Column("pairing_code_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_token_hash", sa.String(255), nullable=True),
        sa.Column("platform", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("mac_address", sa.String(17), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("serial_number", sa.String(128), nullable=True),
        sa.Column("tv_brand", sa.String(32), nullable=True),
        sa.Column("tv_model", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="unpaired"),
        sa.Column("app_version", sa.String(32), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_manifest_version", sa.String(64), nullable=True),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("uptime_sec", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_devices_name", "devices", ["name"])
    op.create_index("ix_devices_pairing_code", "devices", ["pairing_code"])
    op.create_index("ix_devices_mac_address", "devices", ["mac_address"])

    # ===== M:N table =====
    op.create_table(
        "player_group_members",
        sa.Column("player_group_id", sa.Uuid(), sa.ForeignKey("player_groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True),
    )

    # ===== contents =====
    op.create_table(
        "contents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("thumbnail_key", sa.String(512), nullable=True),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("approval_status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("approved_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contents_name", "contents", ["name"])
    op.create_index("ix_contents_sha256", "contents", ["sha256"])

    # ===== presentations =====
    op.create_table(
        "presentations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("layout_json", sa.JSON(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_presentations_name", "presentations", ["name"])

    op.create_table(
        "presentation_zones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("presentation_id", sa.Uuid(), sa.ForeignKey("presentations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_key", sa.String(64), nullable=False),
        sa.Column("content_id", sa.Uuid(), sa.ForeignKey("contents.id"), nullable=False),
        sa.Column("params_json", sa.JSON(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_presentation_zones_presentation_id", "presentation_zones", ["presentation_id"])


def downgrade() -> None:
    op.drop_table("presentation_zones")
    op.drop_table("presentations")
    op.drop_table("contents")
    op.drop_table("player_group_members")
    op.drop_table("devices")
    op.drop_table("player_groups")
