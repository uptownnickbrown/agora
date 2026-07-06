"""players.is_visitor (demo drop-ins hidden from instructor views)

Revision ID: d4f7b3a9e2c1
Revises: c9e4a2b7d1f5
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4f7b3a9e2c1'
down_revision = 'c9e4a2b7d1f5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('players', sa.Column('is_visitor', sa.Boolean(),
                                       server_default=sa.text('false'),
                                       nullable=False))


def downgrade() -> None:
    op.drop_column('players', 'is_visitor')
