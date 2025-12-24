import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 1. Import your models and Base
import models 
from database import Base
target_metadata = Base.metadata  # This allows 'autogenerate' to work

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # 2. Get the URL from environment variable or use a local default
    # Note: Alembic needs a sync driver (psycopg2), not an async one (asyncpg)
    url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/trade_bot_db")
    if "asyncpg" in url:
        url = url.replace("asyncpg", "psycopg2")

    # Override the sqlalchemy.url in the config
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuratio
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    # You can implement run_migrations_offline similarly if needed
    pass
else:
    run_migrations_online()