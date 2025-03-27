import os
import sys
import importlib
import urllib.parse
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config, AsyncEngine
from sqlmodel import SQLModel
from alembic import context
from core.config import settings

# Dynamically import all models from the models/ folder
models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
for filename in os.listdir(models_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = f"models.{filename[:-3]}"
        importlib.import_module(module_name)

config = context.config


# Properly handle URL encoding for password
# def sanitize_db_url(url: str) -> str:
#     """
#     Sanitize database URL to handle special characters in password
#     """
#     # Parse the URL
#     parsed_url = urllib.parse.urlparse(url)
#
#     # Decode the password to handle special characters
#     netloc_parts = parsed_url.netloc.split('@')
#     if len(netloc_parts) > 1:
#         auth_parts = netloc_parts[0].split(':')
#         if len(auth_parts) > 1:
#             # URL decode the password
#             decoded_password = urllib.parse.unquote(auth_parts[1])
#
#             # Reconstruct the URL with decoded password
#             new_auth = f"{auth_parts[0]}:{decoded_password}"
#             new_netloc = f"{new_auth}@{netloc_parts[1]}"
#
#             # Reconstruct the full URL
#             sanitized_url = urllib.parse.urlunparse((
#                 parsed_url.scheme,
#                 new_netloc,
#                 parsed_url.path,
#                 parsed_url.params,
#                 parsed_url.query,
#                 parsed_url.fragment
#             ))
#             return sanitized_url
#
#     return url

def sanitize_db_url(url: str) -> str:
    parsed_url = urllib.parse.urlparse(url)
    netloc_parts = parsed_url.netloc.split('@')
    if len(netloc_parts) > 1:
        auth_parts = netloc_parts[0].split(':')
        if len(auth_parts) > 1:
            # Decode the password and then re-encode it
            decoded_password = urllib.parse.unquote(auth_parts[1])
            encoded_password = urllib.parse.quote(decoded_password)
            new_auth = f"{auth_parts[0]}:{encoded_password}"
            new_netloc = f"{new_auth}@{netloc_parts[1]}"
            sanitized_url = urllib.parse.urlunparse((
                parsed_url.scheme,
                new_netloc,
                parsed_url.path,
                parsed_url.params,
                parsed_url.query,
                parsed_url.fragment
            ))
            return sanitized_url
    return url


# Sanitize the database URL
ASYNC_DB_URL = sanitize_db_url(settings.SQLALCHEMY_DATABASE_URI).replace("%", "%%")
# ASYNC_DB_URL = sanitize_db_url(settings.SQLALCHEMY_DATABASE_URI)
# ASYNC_DB_URL = settings.SQLALCHEMY_DATABASE_URI
print(f"Sanitized DB URL: {ASYNC_DB_URL}")  # Debugging statement
# Set the database URL (use the sanitized URL directly)
config.set_main_option("sqlalchemy.url", ASYNC_DB_URL)

# This line sets up loggers
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the metadata for migrations
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in async mode."""
    # Explicitly create the async engine
    connectable: AsyncEngine = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.begin() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


# Determine migration mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
