"""add_enviado_estado

Revision ID: 07900fa3de2e
Revises: 7ddffe8f2fda
Create Date: 2026-08-29 06:53:31.418465

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07900fa3de2e'
down_revision: Union[str, None] = '7ddffe8f2fda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
