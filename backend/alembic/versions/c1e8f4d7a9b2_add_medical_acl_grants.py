"""add medical acl grants

Revision ID: c1e8f4d7a9b2
Revises: a4f7c9d2b1e3
Create Date: 2026-06-21 02:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1e8f4d7a9b2'
down_revision: Union[str, None] = 'a4f7c9d2b1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_table(
        'medical_acl_grants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),
        sa.Column('grantee_user_id', sa.Integer(), nullable=False),
        sa.Column('actions_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['grantee_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_user_id', 'grantee_user_id', name='uq_medical_acl_owner_grantee'),
    )
    with op.batch_alter_table('medical_acl_grants', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_medical_acl_grants_owner_user_id'), ['owner_user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_medical_acl_grants_grantee_user_id'), ['grantee_user_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('medical_acl_grants', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_medical_acl_grants_grantee_user_id'))
        batch_op.drop_index(batch_op.f('ix_medical_acl_grants_owner_user_id'))
    op.drop_table('medical_acl_grants')
