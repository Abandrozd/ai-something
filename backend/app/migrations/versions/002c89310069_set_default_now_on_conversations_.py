"""set default now on conversations.created_at

Revision ID: 002c89310069
Revises: d5d15e71f33f
Create Date: 2026-10-29 20:05:50.240630

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002c89310069'
down_revision: Union[str, Sequence[str], None] = 'd5d15e71f33f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'conversations',
        'created_at',
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text('now()'),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
