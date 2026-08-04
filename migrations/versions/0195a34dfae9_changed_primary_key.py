"""Changed primary key

Revision ID: 0195a34dfae9
Revises: a32626b4c49a
Create Date: 2026-08-03 18:58:55.372115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0195a34dfae9'
down_revision: Union[str, Sequence[str], None] = 'a32626b4c49a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'locations_new',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE'
        )
    )

    op.execute("""
        INSERT INTO locations_new (
            user_id,
            timestamp,
            latitude,
            longitude,
            speed
        )
        SELECT
            user_id,
            timestamp,
            latitude,
            longitude,
            speed
        FROM locations
    """)

    op.drop_table('locations')
    op.rename_table('locations_new', 'locations')

    op.create_index(
        'locations',
        ['id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.create_table(
        'locations_old',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('timestamp')
    )

    op.execute("""
        INSERT INTO locations_old (
            user_id,
            timestamp,
            latitude,
            longitude,
            speed
        )
        SELECT
            user_id,
            timestamp,
            latitude,
            longitude,
            speed
        FROM locations
    """)

    op.drop_table('locations')
    op.rename_table('locations_old', 'locations')