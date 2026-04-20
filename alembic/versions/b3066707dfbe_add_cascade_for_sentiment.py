"""add cascade for sentiment

Revision ID: b3066707dfbe
Revises: 2fa0adcca67d
Create Date: 2026-04-17 16:06:03.598147

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b3066707dfbe"
down_revision: Union[str, Sequence[str], None] = "2fa0adcca67d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "sentiment_conversation_id_fkey", "sentiment", type_="foreignkey"
    )
    op.create_foreign_key(
        "sentiment_conversation_id_fkey",
        "sentiment",
        "conversation",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "sentiment_conversation_id_fkey", "sentiment", type_="foreignkey"
    )
    op.create_foreign_key(
        "sentiment_conversation_id_fkey",
        "sentiment",
        "conversation",
        ["conversation_id"],
        ["id"],
    )
