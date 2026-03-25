"""add applied to jobs

Revision ID: b1c3d4e5f6a7
Revises: a9ef2b2e61c9
Create Date: 2026-03-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c3d4e5f6a7'
down_revision: Union[str, None] = 'a9ef2b2e61c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('applied', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('jobs', 'applied')
