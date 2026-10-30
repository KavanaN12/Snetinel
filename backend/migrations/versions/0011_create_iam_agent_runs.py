"""create persisted IAM agent runs

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-17 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iam_agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("lifecycle", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.JSON(), nullable=False),
        sa.Column("baseline_path_count", sa.Integer(), nullable=False),
        sa.Column("final_path_count", sa.Integer(), nullable=False),
        sa.Column("evaluation", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_iam_agent_runs_workspace_id"),
        "iam_agent_runs",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_iam_agent_runs_workspace_id"), table_name="iam_agent_runs")
    op.drop_table("iam_agent_runs")
