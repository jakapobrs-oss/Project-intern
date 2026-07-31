"""users.locked_until — ล็อกชั่วคราวเมื่อกรอกรหัสผิดเกินกำหนด (§26)

เพิ่มคอลัมน์เดียว ว่างได้ (nullable) → ไม่แตะข้อมูลเดิม ย้อนกลับได้ด้วยการ drop

ทำไมต้องมี: เดิม lockout เขียนลง is_locked ซึ่งเป็น boolean ถาวร ปลดได้ทางเดียว
คือให้ admin คนอื่นมาปลด — ถ้าระบบมี super_admin บัญชีเดียวแล้วบัญชีนั้นโดนล็อก
จะไม่มีใครปลดได้เลย และใครที่รู้แค่ชื่อผู้ใช้ก็จงใจกรอกรหัสผิดเพื่อปิดบัญชีคนอื่น
ได้ถาวร (account-lockout DoS) — ดู services/auth_service.py

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-01
"""
from typing import Union
from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
