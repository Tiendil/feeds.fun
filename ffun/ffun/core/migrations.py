from yoyo import get_backend, read_migrations
from yoyo.migrations import MigrationList

from ffun.application.settings import settings as app_settings
from ffun.core.utils import package_root

ffun_root = package_root()


async def apply_all() -> None:
    migrations: MigrationList = read_migrations(f"{ffun_root}/*/migrations")

    with get_backend(app_settings.postgresql.dsn_yoyo, "yoyo_migrations") as backend:
        with backend.lock():
            migrations_to_apply: MigrationList = backend.to_apply(migrations)
            backend.apply_migrations(migrations_to_apply)


async def rollback_all() -> None:
    migrations: MigrationList = read_migrations(f"{ffun_root}/*/migrations")

    with get_backend(app_settings.postgresql.dsn_yoyo, "yoyo_migrations") as backend:
        with backend.lock():
            migrations_to_rollback: MigrationList = backend.to_rollback(migrations)
            backend.rollback_migrations(migrations_to_rollback)
