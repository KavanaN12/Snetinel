"""create findings table

Revision ID: 0008
Revises: 0007_create_attack_paths_table
Create Date: 2026-07-16 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("evidence_subgraph", sa.JSON(), nullable=True),
        sa.Column("affected_resource_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_findings_workspace_id"), "findings", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_findings_workspace_id"), table_name="findings")
    op.drop_table("findings")
