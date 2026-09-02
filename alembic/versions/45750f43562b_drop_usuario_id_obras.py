"""drop_usuario_id_obras

Revision ID: 45750f43562b
Revises: 8b4ca75dd3a9
Create Date: 2026-09-02 12:45:19.349140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '45750f43562b'
down_revision: Union[str, None] = '8b4ca75dd3a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Set default values for null columns first!
    op.execute("UPDATE empresas SET created_at = NOW() WHERE created_at IS NULL")
    op.execute("UPDATE empresas SET updated_at = NOW() WHERE updated_at IS NULL")
    op.alter_column('empresas', 'created_at', nullable=False)
    op.alter_column('empresas', 'updated_at', nullable=False)
    
    op.drop_constraint('obras_usuario_id_fkey', 'obras', type_='foreignkey')
    op.drop_column('obras', 'usuario_id')
    
    # Just fix the rest
    pass

def downgrade() -> None:
    pass
