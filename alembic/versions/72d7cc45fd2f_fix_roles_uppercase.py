"""fix_roles_uppercase

Revision ID: 72d7cc45fd2f
Revises: cdde6a720902
Create Date: 2026-08-28 12:23:30.788457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72d7cc45fd2f'
down_revision: Union[str, None] = 'cdde6a720902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregamos los roles en mayúscula porque la migración anterior los añadió en minúscula,
    # causando DataError (invalid input value for enum rolusuario)
    op.execute("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'DIRECTOR'")
    op.execute("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'LECTOR'")


def downgrade() -> None:
    pass
