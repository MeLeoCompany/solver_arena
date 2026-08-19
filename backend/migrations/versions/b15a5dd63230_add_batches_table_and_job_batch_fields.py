"""add batches table and job batch fields

Revision ID: b15a5dd63230
Revises: fc7b10822ec6
Create Date: 2026-08-18 16:42:14.585248

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b15a5dd63230'
down_revision: Union[str, Sequence[str], None] = 'fc7b10822ec6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('batches',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('solver', sa.String(), nullable=False),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.Column('completed', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # SQLite can't ALTER a constraint onto an existing table — batch mode
    # does the copy-and-move dance for us. Split into two blocks: alembic's
    # batch-mode column reordering chokes with a spurious circular
    # dependency error when adding several plain columns and a new FK in
    # one go.
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.add_column(sa.Column('original_filename', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('batch_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('batch_index', sa.Integer(), nullable=True))
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.create_foreign_key('fk_jobs_batch_id_batches', 'batches', ['batch_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.drop_constraint('fk_jobs_batch_id_batches', type_='foreignkey')
    with op.batch_alter_table('jobs') as batch_op:
        batch_op.drop_column('batch_index')
        batch_op.drop_column('batch_id')
        batch_op.drop_column('original_filename')
    op.drop_table('batches')
