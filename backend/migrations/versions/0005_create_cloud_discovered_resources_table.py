"""create cloud discovered resources table

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cloud_discovered_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "discovery_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("arn", sa.String(1000), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cloud_discovered_resources_workspace_id", "cloud_discovered_resources", ["workspace_id"])
    op.create_index("ix_cloud_discovered_resources_discovery_run_id", "cloud_discovered_resources", ["discovery_run_id"])
    op.create_index("ix_cloud_discovered_resources_resource_type", "cloud_discovered_resources", ["resource_type"])
    op.create_index("ix_cloud_discovered_resources_resource_id", "cloud_discovered_resources", ["resource_id"])
    op.create_unique_constraint(
        "uq_cloud_resources_workspace_type_id",
        "cloud_discovered_resources",
        ["workspace_id", "resource_type", "resource_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_cloud_resources_workspace_type_id", table_name="cloud_discovered_resources", type_="unique")
    op.drop_index("ix_cloud_discovered_resources_resource_id", table_name="cloud_discovered_resources")
    op.drop_index("ix_cloud_discovered_resources_resource_type", table_name="cloud_discovered_resources")
    op.drop_index("ix_cloud_discovered_resources_discovery_run_id", table_name="cloud_discovered_resources")
    op.drop_index("ix_cloud_discovered_resources_workspace_id", table_name="cloud_discovered_resources")
    op.drop_table("cloud_discovered_resources")
