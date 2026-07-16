"""create attack paths table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attack_paths",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attack_type", sa.String(100), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("details", sa.JSON(), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_attack_paths_workspace_id", "attack_paths", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_attack_paths_workspace_id", table_name="attack_paths")
    op.drop_table("attack_paths")
