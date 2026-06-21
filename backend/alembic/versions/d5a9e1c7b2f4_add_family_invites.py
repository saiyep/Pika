"""add family invites

Revision ID: d5a9e1c7b2f4
Revises: c1e8f4d7a9b2
Create Date: 2026-06-21 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a9e1c7b2f4'
down_revision: Union[str, None] = 'c1e8f4d7a9b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'family_invites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('inviter_user_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='active', nullable=False),
        sa.Column('used_by_user_id', sa.Integer(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['family_groups.id']),
        sa.ForeignKeyConstraint(['inviter_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['used_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_family_invite_code'),
    )
    with op.batch_alter_table('family_invites', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_family_invites_family_id'), ['family_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_family_invites_inviter_user_id'), ['inviter_user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_family_invites_code'), ['code'], unique=False)
        batch_op.create_index(batch_op.f('ix_family_invites_used_by_user_id'), ['used_by_user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('family_invites', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_family_invites_used_by_user_id'))
        batch_op.drop_index(batch_op.f('ix_family_invites_code'))
        batch_op.drop_index(batch_op.f('ix_family_invites_inviter_user_id'))
        batch_op.drop_index(batch_op.f('ix_family_invites_family_id'))
    op.drop_table('family_invites')
