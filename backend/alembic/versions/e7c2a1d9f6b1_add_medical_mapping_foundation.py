"""add medical mapping foundation

Revision ID: e7c2a1d9f6b1
Revises: d5a9e1c7b2f4
Create Date: 2026-06-28 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7c2a1d9f6b1'
down_revision: Union[str, None] = 'd5a9e1c7b2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CATEGORY_DEFAULTS = [
    ("blood_routine", "血常规", 10),
    ("urine_routine", "尿常规", 20),
    ("liver_kidney", "肝肾功能", 30),
    ("tumor_marker", "肿瘤标志物", 40),
    ("thyroid", "甲状腺功能", 50),
]


def upgrade() -> None:
    op.create_table(
        'medical_report_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('category_key', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['family_groups.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('family_id', 'category_key', name='uq_medical_category_family_key'),
    )
    with op.batch_alter_table('medical_report_categories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_medical_report_categories_family_id'), ['family_id'], unique=False)

    op.create_table(
        'medical_metric_dictionary',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('canonical_key', sa.String(), nullable=False),
        sa.Column('canonical_name', sa.String(), nullable=False),
        sa.Column('canonical_unit', sa.String(), nullable=True),
        sa.Column('category_key', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('canonical_key'),
    )
    with op.batch_alter_table('medical_metric_dictionary', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_medical_metric_dictionary_canonical_key'), ['canonical_key'], unique=False)
        batch_op.create_index(batch_op.f('ix_medical_metric_dictionary_category_key'), ['category_key'], unique=False)

    op.create_table(
        'medical_metric_aliases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('dictionary_id', sa.Integer(), nullable=False),
        sa.Column('alias_name', sa.String(), nullable=False),
        sa.Column('alias_unit', sa.String(), nullable=True),
        sa.Column('hospital_hint', sa.String(), nullable=True),
        sa.Column('report_type_hint', sa.String(), nullable=True),
        sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['dictionary_id'], ['medical_metric_dictionary.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dictionary_id', 'alias_name', 'alias_unit', 'hospital_hint', name='uq_medical_metric_alias_compound'),
    )
    with op.batch_alter_table('medical_metric_aliases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_medical_metric_aliases_dictionary_id'), ['dictionary_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_medical_metric_aliases_hospital_hint'), ['hospital_hint'], unique=False)

    op.create_table(
        'medical_report_metric_maps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_metric_id', sa.Integer(), nullable=False),
        sa.Column('dictionary_id', sa.Integer(), nullable=True),
        sa.Column('alias_id', sa.Integer(), nullable=True),
        sa.Column('match_status', sa.String(), server_default='unmapped', nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('mapped_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['alias_id'], ['medical_metric_aliases.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['dictionary_id'], ['medical_metric_dictionary.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['mapped_by'], ['users.id']),
        sa.ForeignKeyConstraint(['report_metric_id'], ['medical_report_metrics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_metric_id', name='uq_medical_report_metric_map_metric'),
    )
    with op.batch_alter_table('medical_report_metric_maps', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_medical_report_metric_maps_report_metric_id'), ['report_metric_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_medical_report_metric_maps_dictionary_id'), ['dictionary_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_medical_report_metric_maps_alias_id'), ['alias_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_medical_report_metric_maps_mapped_by'), ['mapped_by'], unique=False)

    op.create_table(
        'medical_user_focus_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('dictionary_id', sa.Integer(), nullable=False),
        sa.Column('category_key', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['dictionary_id'], ['medical_metric_dictionary.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'dictionary_id', name='uq_medical_user_focus_metric'),
    )
    with op.batch_alter_table('medical_user_focus_metrics', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_medical_user_focus_metrics_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_medical_user_focus_metrics_dictionary_id'), ['dictionary_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_medical_user_focus_metrics_category_key'), ['category_key'], unique=False)

    conn = op.get_bind()
    family_rows = conn.execute(sa.text("SELECT id FROM family_groups")).fetchall()
    if family_rows:
        values = []
        for (family_id,) in family_rows:
            for key, name, order in _CATEGORY_DEFAULTS:
                values.append(
                    {
                        "family_id": family_id,
                        "category_key": key,
                        "display_name": name,
                        "enabled": True,
                        "sort_order": order,
                    }
                )
        op.bulk_insert(
            sa.table(
                "medical_report_categories",
                sa.column("family_id", sa.Integer),
                sa.column("category_key", sa.String),
                sa.column("display_name", sa.String),
                sa.column("enabled", sa.Boolean),
                sa.column("sort_order", sa.Integer),
            ),
            values,
        )


def downgrade() -> None:
    with op.batch_alter_table('medical_user_focus_metrics', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_medical_user_focus_metrics_category_key'))
        batch_op.drop_index(batch_op.f('ix_medical_user_focus_metrics_dictionary_id'))
        batch_op.drop_index(batch_op.f('ix_medical_user_focus_metrics_user_id'))
    op.drop_table('medical_user_focus_metrics')

    with op.batch_alter_table('medical_report_metric_maps', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_medical_report_metric_maps_mapped_by'))
        batch_op.drop_index(batch_op.f('ix_medical_report_metric_maps_alias_id'))
        batch_op.drop_index(batch_op.f('ix_medical_report_metric_maps_dictionary_id'))
        batch_op.drop_index(batch_op.f('ix_medical_report_metric_maps_report_metric_id'))
    op.drop_table('medical_report_metric_maps')

    with op.batch_alter_table('medical_metric_aliases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_medical_metric_aliases_hospital_hint'))
        batch_op.drop_index(batch_op.f('ix_medical_metric_aliases_dictionary_id'))
    op.drop_table('medical_metric_aliases')

    with op.batch_alter_table('medical_metric_dictionary', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_medical_metric_dictionary_category_key'))
        batch_op.drop_index(batch_op.f('ix_medical_metric_dictionary_canonical_key'))
    op.drop_table('medical_metric_dictionary')

    with op.batch_alter_table('medical_report_categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_medical_report_categories_family_id'))
    op.drop_table('medical_report_categories')
