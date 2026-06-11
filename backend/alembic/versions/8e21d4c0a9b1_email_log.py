"""email_log

Revision ID: 8e21d4c0a9b1
Revises: ff93cfaaa47b
Create Date: 2026-06-11 16:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '8e21d4c0a9b1'
down_revision = 'ff93cfaaa47b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('email_log',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('world_id', sa.Uuid(), nullable=True),
    sa.Column('to_email', sa.String(length=320), nullable=False),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('ref', sa.String(length=40), nullable=False),
    sa.Column('subject', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('provider_id', sa.String(length=80), nullable=False),
    sa.Column('body_text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_log_world_id'), 'email_log', ['world_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_log_world_id'), table_name='email_log')
    op.drop_table('email_log')
