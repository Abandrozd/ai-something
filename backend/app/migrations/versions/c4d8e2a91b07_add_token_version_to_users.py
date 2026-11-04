"""add token_version to users

Revision ID: c4d8e2a91b07
Revises: 5ec1c41f3eaa
Create Date: 2026-11-04 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d8e2a91b07"
down_revision: Union[str, Sequence[str], None] = "5ec1c41f3eaa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
