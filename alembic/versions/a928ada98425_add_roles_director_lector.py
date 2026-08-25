"""add_roles_director_lector

Revision ID: a928ada98425
Revises: 412e888226df
Create Date: 2026-08-26 01:10:28.400626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a928ada98425'
down_revision: Union[str, None] = '412e888226df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'director'")
    op.execute("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'lector'")


def downgrade() -> None:
    # PostgreSQL doesn't support DROP VALUE for ENUMs.
    pass
