"""haggle sessions (the caravan minigame)

Revision ID: b7d2e1f4c8a3
Revises: 8e21d4c0a9b1
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7d2e1f4c8a3'
down_revision = '8e21d4c0a9b1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'haggle_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('world_id', sa.Uuid(), nullable=False),
        sa.Column('player_id', sa.Uuid(), nullable=False),
        sa.Column('world_day', sa.Integer(), nullable=False),
        sa.Column('good_id', sa.String(length=24), nullable=False),
        sa.Column('side', sa.String(length=12), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('reservation', sa.Integer(), nullable=False),
        sa.Column('visitor', sa.String(length=60), nullable=False),
        sa.Column('portrait', sa.String(length=24), nullable=False),
        sa.Column('offers', sa.JSON(), nullable=False),
        sa.Column('state', sa.String(length=12), nullable=False),
        sa.Column('accepted_price', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('world_id', 'player_id', 'world_day'),
    )
    op.create_index(op.f('ix_haggle_sessions_player_id'), 'haggle_sessions',
                    ['player_id'], unique=False)
    op.create_index(op.f('ix_haggle_sessions_world_id'), 'haggle_sessions',
                    ['world_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_haggle_sessions_world_id'), table_name='haggle_sessions')
    op.drop_index(op.f('ix_haggle_sessions_player_id'), table_name='haggle_sessions')
    op.drop_table('haggle_sessions')
