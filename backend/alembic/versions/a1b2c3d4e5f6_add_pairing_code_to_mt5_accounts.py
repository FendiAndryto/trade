"""add_pairing_code_to_mt5_accounts

Revision ID: a1b2c3d4e5f6
Revises: cc06682d5832
Create Date: 2026-10-15 19:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "cc06682d5832"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mt5_accounts", sa.Column("pairing_code", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_mt5_accounts_pairing_code"), "mt5_accounts", ["pairing_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mt5_accounts_pairing_code"), table_name="mt5_accounts")
    op.drop_column("mt5_accounts", "pairing_code")
