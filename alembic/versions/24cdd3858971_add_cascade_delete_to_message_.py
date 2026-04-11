"""add_cascade_delete_to_message_conversation_fkey

Revision ID: 24cdd3858971
Revises: 13f56ad79386
Create Date: 2026-04-09 15:16:24.399752

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "24cdd3858971"
down_revision: Union[str, Sequence[str], None] = "13f56ad79386"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("message_conversation_id_fkey", "message", type_="foreignkey")
    op.create_foreign_key(
        "message_conversation_id_fkey",
        "message",
        "conversation",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("message_conversation_id_fkey", "message", type_="foreignkey")
    op.create_foreign_key(
        "message_conversation_id_fkey",
        "message",
        "conversation",
        ["conversation_id"],
        ["id"],
    )
