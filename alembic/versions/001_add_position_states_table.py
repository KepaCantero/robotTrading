"""Add position_states table

Revision ID: 001_add_position_states_table
Revises:
Create Date: 2026-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_position_states_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create position_states table."""
    op.create_table(
        'position_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('monitor_id', sa.String(length=255), nullable=False),
        sa.Column('positions_json', sa.Text(), nullable=False),
        sa.Column('last_sync', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_position_states_monitor_id', 'position_states', ['monitor_id'])


def downgrade() -> None:
    """Drop position_states table."""
    op.drop_index('ix_position_states_monitor_id', table_name='position_states')
    op.drop_table('position_states')
