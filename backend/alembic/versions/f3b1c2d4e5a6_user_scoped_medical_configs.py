"""user scoped medical configs

Revision ID: f3b1c2d4e5a6
Revises: e7c2a1d9f6b1
Create Date: 2026-06-28 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3b1c2d4e5a6'
down_revision: Union[str, None] = 'e7c2a1d9f6b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('medical_report_categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_medical_report_categories_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key('fk_medical_report_categories_user_id_users', 'users', ['user_id'], ['id'])

    op.execute(
        sa.text(
            """
            UPDATE medical_report_categories
            SET user_id = (
                SELECT fm.user_id
                FROM family_memberships fm
                WHERE fm.family_id = medical_report_categories.family_id
                  AND fm.is_active = 1
                ORDER BY fm.family_role = 'admin' DESC, fm.user_id ASC
                LIMIT 1
            )
            """
        )
    )

    op.execute(sa.text("DELETE FROM medical_report_categories WHERE user_id IS NULL"))

    with op.batch_alter_table('medical_report_categories', schema=None) as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_constraint('uq_medical_category_family_key', type_='unique')
        batch_op.create_unique_constraint('uq_medical_category_user_key', ['user_id', 'category_key'])

    with op.batch_alter_table('medical_metric_aliases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_user_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_medical_metric_aliases_owner_user_id'), ['owner_user_id'], unique=False)
        batch_op.create_foreign_key('fk_medical_metric_aliases_owner_user_id_users', 'users', ['owner_user_id'], ['id'])

    op.execute(
        sa.text(
            """
            UPDATE medical_metric_aliases
            SET owner_user_id = (
                SELECT mr.subject_id
                FROM medical_report_metric_maps mm
                JOIN medical_report_metrics m ON m.id = mm.report_metric_id
                JOIN medical_reports mr ON mr.id = m.report_id
                WHERE mm.alias_id = medical_metric_aliases.id
                  AND mr.subject_id IS NOT NULL
                ORDER BY mr.id DESC
                LIMIT 1
            )
            WHERE owner_user_id IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE medical_metric_aliases
            SET owner_user_id = (
                SELECT mr.uploader_id
                FROM medical_report_metric_maps mm
                JOIN medical_report_metrics m ON m.id = mm.report_metric_id
                JOIN medical_reports mr ON mr.id = m.report_id
                WHERE mm.alias_id = medical_metric_aliases.id
                ORDER BY mr.id DESC
                LIMIT 1
            )
            WHERE owner_user_id IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE medical_metric_aliases
            SET owner_user_id = (
                SELECT id FROM users ORDER BY id ASC LIMIT 1
            )
            WHERE owner_user_id IS NULL
            """
        )
    )

    with op.batch_alter_table('medical_metric_aliases', schema=None) as batch_op:
        batch_op.alter_column('owner_user_id', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_constraint('uq_medical_metric_alias_compound', type_='unique')
        batch_op.create_unique_constraint(
            'uq_medical_metric_alias_owner_compound',
            ['owner_user_id', 'dictionary_id', 'alias_name', 'alias_unit', 'hospital_hint'],
        )


def downgrade() -> None:
    with op.batch_alter_table('medical_metric_aliases', schema=None) as batch_op:
        batch_op.drop_constraint('uq_medical_metric_alias_owner_compound', type_='unique')
        batch_op.create_unique_constraint(
            'uq_medical_metric_alias_compound',
            ['dictionary_id', 'alias_name', 'alias_unit', 'hospital_hint'],
        )
        batch_op.drop_constraint('fk_medical_metric_aliases_owner_user_id_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_medical_metric_aliases_owner_user_id'))
        batch_op.drop_column('owner_user_id')

    with op.batch_alter_table('medical_report_categories', schema=None) as batch_op:
        batch_op.drop_constraint('uq_medical_category_user_key', type_='unique')
        batch_op.create_unique_constraint('uq_medical_category_family_key', ['family_id', 'category_key'])
        batch_op.drop_constraint('fk_medical_report_categories_user_id_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_medical_report_categories_user_id'))
        batch_op.drop_column('user_id')
