"""add uppercase ENVIADO to enum

Revision ID: 0ce2598c4480
Revises: 071dbf6154e5
Create Date: 2026-09-02 12:06:15.527648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ce2598c4480'
down_revision: Union[str, None] = '071dbf6154e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Disable transaction blocks for ALTER TYPE ... ADD VALUE
    op.execute("COMMIT")
    op.execute("ALTER TYPE estadopresupuesto ADD VALUE IF NOT EXISTS 'ENVIADO'")


def downgrade() -> None:
    pass
