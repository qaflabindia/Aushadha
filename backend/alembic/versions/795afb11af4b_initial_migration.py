"""Initial_migration

Revision ID: 795afb11af4b
Revises: 
Create Date: 2026-03-09 14:43:23.735602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '795afb11af4b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ui_translations is managed by ensure_table() in ui_translations.py and must
    # NOT be touched here — dropping it would wipe the translation cache.
    op.add_column('patients', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'patients', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.add_column('users', sa.Column('hashed_password', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'hashed_password')
    op.drop_constraint(None, 'patients', type_='foreignkey')
    op.drop_column('patients', 'user_id')
