import asyncio

import httpx
import typer

from ffun.application.application import with_app
from ffun.auth.settings import settings as auth_settings

from ..application import app


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
        print(response.status_code)
        print(response.json())


@app.command()
def supertokens_create_admin(email: str, password: str) -> None:
    asyncio.run(run_supertokens_create_admin(email, password))
