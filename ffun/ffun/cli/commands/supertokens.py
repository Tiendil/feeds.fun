import asyncio

import httpx

from ffun.auth.settings import settings as auth_settings
from ffun.cli.application import app
from ffun.core import logging

logger = logging.get_module_logger()


async def run_supertokens_create_admin(email: str, password: str) -> None:
    url = f"{auth_settings.supertokens.connection_uri}/recipe/dashboard/user"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            follow_redirects=True,
            headers={
                "rid": "dashboard",
                "api-key": auth_settings.supertokens.api_key,
                "Content-Type": "application/json",
            },
            json={"email": email, "password": password},
        )
        logger.info("status_code", status_code=response.status_code)
        logger.info("response", response.json())


@app.command()
def supertokens_create_admin(email: str, password: str) -> None:
    asyncio.run(run_supertokens_create_admin(email, password))
