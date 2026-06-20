"""family groups and managed users

Revision ID: a4f7c9d2b1e3
Revises: af6a6363811c
Create Date: 2026-06-20 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4f7c9d2b1e3'
down_revision: Union[str, None] = 'af6a6363811c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'family_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('family_groups', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_family_groups_owner_user_id'), ['owner_user_id'], unique=False)

    op.create_table(
        'family_memberships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('family_role', sa.String(), server_default='member', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['family_groups.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('family_id', 'user_id', name='uq_family_user'),
    )
    with op.batch_alter_table('family_memberships', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_family_memberships_family_id'), ['family_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_family_memberships_user_id'), ['user_id'], unique=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('openid', existing_type=sa.String(), nullable=True)
        batch_op.add_column(sa.Column('account_type', sa.String(), server_default='wechat', nullable=False))
        batch_op.add_column(sa.Column('status', sa.String(), server_default='active', nullable=False))

    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id, nickname, role FROM users")).fetchall()
    for u in users:
        name = (u.nickname or f"family-{u.id}").strip() or f"family-{u.id}"
        family_id = conn.execute(
            sa.text("INSERT INTO family_groups(name, owner_user_id) VALUES (:name, :owner) RETURNING id"),
            {"name": name, "owner": u.id},
        ).scalar_one()
        family_role = 'admin' if (u.role or '').lower() == 'admin' else 'member'
        conn.execute(
            sa.text(
                "INSERT INTO family_memberships(family_id, user_id, family_role, is_active) "
                "VALUES (:family_id, :user_id, :family_role, 1)"
            ),
            {"family_id": family_id, "user_id": u.id, "family_role": family_role},
        )


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('status')
        batch_op.drop_column('account_type')
        batch_op.alter_column('openid', existing_type=sa.String(), nullable=False)

    with op.batch_alter_table('family_memberships', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_family_memberships_user_id'))
        batch_op.drop_index(batch_op.f('ix_family_memberships_family_id'))
    op.drop_table('family_memberships')

    with op.batch_alter_table('family_groups', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_family_groups_owner_user_id'))
    op.drop_table('family_groups')
