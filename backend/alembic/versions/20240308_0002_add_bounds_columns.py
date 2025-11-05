"""add bounds columns to managed_databases

Revision ID: 20240308_0002
Revises: 20240308_0001
Create Date: 2025-11-05 22:52:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20240308_0002"
down_revision: Union[str, None] = "20240308_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("managed_databases", sa.Column("min_lon", sa.Float(), nullable=True))
    op.add_column("managed_databases", sa.Column("min_lat", sa.Float(), nullable=True))
    op.add_column("managed_databases", sa.Column("max_lon", sa.Float(), nullable=True))
    op.add_column("managed_databases", sa.Column("max_lat", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("managed_databases", "max_lat")
    op.drop_column("managed_databases", "max_lon")
    op.drop_column("managed_databases", "min_lat")
    op.drop_column("managed_databases", "min_lon")
