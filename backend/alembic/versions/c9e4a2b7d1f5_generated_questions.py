"""generated questions (Pip writes practice items on the fly)

Revision ID: c9e4a2b7d1f5
Revises: b7d2e1f4c8a3
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa


revision = 'c9e4a2b7d1f5'
down_revision = 'b7d2e1f4c8a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'generated_questions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('world_id', sa.Uuid(), nullable=False),
        sa.Column('player_id', sa.Uuid(), nullable=False),
        sa.Column('lo_id', sa.String(length=40), nullable=False),
        sa.Column('world_day', sa.Integer(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('choices', sa.JSON(), nullable=False),
        sa.Column('answer', sa.Integer(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_generated_questions_lo_id'), 'generated_questions',
                    ['lo_id'], unique=False)
    op.create_index(op.f('ix_generated_questions_player_id'), 'generated_questions',
                    ['player_id'], unique=False)
    op.create_index(op.f('ix_generated_questions_world_id'), 'generated_questions',
                    ['world_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_generated_questions_world_id'), table_name='generated_questions')
    op.drop_index(op.f('ix_generated_questions_player_id'), table_name='generated_questions')
    op.drop_index(op.f('ix_generated_questions_lo_id'), table_name='generated_questions')
    op.drop_table('generated_questions')
