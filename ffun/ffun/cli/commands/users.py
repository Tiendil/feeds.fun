import asyncio
import csv
import datetime
import pathlib

import typer

from ffun.application.application import with_app
from ffun.auth import domain as a_domain
from ffun.auth.settings import settings as a_settings
from ffun.core import logging

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_import_users(
    csv_path: pathlib.Path, idp_id: str, verify_internal_users_exists: bool, number: int | None = None
) -> None:  # noqa: CCR001
    idp = a_settings.get_idp_by_external_id(idp_id)

    if idp is None:
        logger.error("idp_not_found", idp_id=idp_id)
        return

    data = []

    logger.info("import_users")

    logger.info("reading_csv", path=str(csv_path))

    with csv_path.open("r", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            user_id = row["user_id"]
            email = row["email"]
            created_at = datetime.datetime.fromtimestamp(int(row["time_joined"]) / 1000)
            data.append((user_id, email, created_at))

    logger.info("csv_read", rows=len(data))

    if number is not None:
        data = data[:number]

    logger.info("starting_import", total_users=len(data))

    async with with_app():
        for user_id, email, created_at in data:
            logger.info("importing_user", user_id=user_id)
            await a_domain.import_user_to_external_service(
                service=idp.internal_id,
                external_user_id=user_id,
                email=email,
                created_at=created_at,
                verify_internal_user_exists=verify_internal_users_exists,
            )

    logger.info("import_users_finished", total_users=len(data))


@cli_app.command()
def import_users_to_idp(
    idp_id: str, csv_path: pathlib.Path, verify_internal_users_exists: bool = True, number: int | None = None
) -> None:
    """Import users from a CSV file to the identity provider.

    Args:
        csv_path (path.Path): Path to the CSV file containing user data.
        idp_id (str): The identity provider ID to which users will be imported.
        verify_internal_users_exists (bool): Whether to verify that internal users exist before importing.
        number (int): Optional number of users to import. If None, all users in the CSV will be imported.

    Format of the CSV file: 3 columns - user_id(str), email(str), time_joined(millisec since epoch)
    """
    asyncio.run(
        run_import_users(
            csv_path=csv_path, idp_id=idp_id, verify_internal_users_exists=verify_internal_users_exists, number=number
        )
    )
