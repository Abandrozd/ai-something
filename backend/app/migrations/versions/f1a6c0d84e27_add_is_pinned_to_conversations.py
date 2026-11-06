"""add is_pinned to conversations

Revision ID: f1a6c0d84e27
Revises: c4d8e2a91b07
Create Date: 2026-11-05 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a6c0d84e27"
down_revision: Union[str, Sequence[str], None] = "c4d8e2a91b07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "is_pinned")
