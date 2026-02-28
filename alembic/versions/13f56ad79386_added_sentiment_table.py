"""added sentiment table

Revision ID: 13f56ad79386
Revises: <to_be_filled>
Create Date: 2026-03-22 16:20:55.305367

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "13f56ad79386"
down_revision: Union[str, Sequence[str], None] = "e59767e882df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sentiment",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("sentiment", sa.Numeric(4, 2), nullable=False, server_default="0.00"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "sentiment >= -10.00 AND sentiment <= 10.00", name="ck_sentiment_range"
        ),
    )
    op.create_index(
        "ix_sentiment_conversation_id",
        "sentiment",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_sentiment_conversation_id", table_name="sentiment")
    op.drop_table("sentiment")
