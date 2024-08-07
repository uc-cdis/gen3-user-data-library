"""initial user lists table

Revision ID: 4c18bd2d556f
Revises: 
Create Date: 2024-07-09 13:18:21.643599

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c18bd2d556f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_lists",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("creator", sa.String, nullable=False, index=True),
        sa.Column("authz", sa.JSON, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column(
            "created_time",
            sa.DateTime(timezone=True),
            nullable=False,
            default=sa.func.now(),
        ),
        sa.Column(
            "updated_time",
            sa.DateTime(timezone=True),
            nullable=False,
            default=sa.func.now(),
        ),
        sa.Column("items", sa.JSON),
        sa.UniqueConstraint("name", "creator", name="_name_creator_uc"),
    )


def downgrade() -> None:
    op.drop_table("user_lists")
