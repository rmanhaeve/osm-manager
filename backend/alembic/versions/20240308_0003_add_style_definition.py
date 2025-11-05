"""add style_definition column to managed_databases

Revision ID: 20240308_0003
Revises: 20240308_0002
Create Date: 2025-11-05 23:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20240308_0003"
down_revision: Union[str, None] = "20240308_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("managed_databases", sa.Column("style_definition", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("managed_databases", "style_definition")
