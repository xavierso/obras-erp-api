"""add_enviado_estado

Revision ID: 0c69c8c270ab
Revises: 07900fa3de2e
Create Date: 2026-08-29 06:54:28.886779

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c69c8c270ab'
down_revision: Union[str, None] = '07900fa3de2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Disable transaction blocks for ALTER TYPE ... ADD VALUE
    op.execute("COMMIT")
    op.execute("ALTER TYPE estadopresupuesto ADD VALUE IF NOT EXISTS 'enviado'")


def downgrade() -> None:
    # Postgres doesn't support removing enum values easily, so we do nothing.
    pass
