import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

# Import Base and ALL module models so autogenerate can see them.
from src.shared.db.session import Base
from src.modules.auth.infrastructure.models import UserModel, RefreshTokenModel  # noqa: F401
from src.modules.discovery.infrastructure.models import DiscoveryRunModel  # noqa: F401
from src.modules.workspace.infrastructure.models import WorkspaceModel  # noqa: F401
from src.modules.graph.infrastructure.models import GraphNodeModel, GraphEdgeModel  # noqa: F401
from src.modules.attack_path.infrastructure.models import AttackPathModel  # noqa: F401
from src.modules.risk_scoring.infrastructure.models import FindingModel  # noqa: F401
from src.modules.audit.infrastructure.models import AuditLogModel  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
