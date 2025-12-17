import datetime
from typing import Any

from ffun.auth.idps.plugin import Plugin as PluginBase
from ffun.core import errors
from ffun.domain import http


class Error(errors.Error):
    pass


class CanNotGetAccessToken(Error):
    pass


class CanNotCallAdminAPI(Error):
    pass


class Plugin(PluginBase):
    __slots__ = ("entrypoint", "service_realm", "client_id", "client_secret", "_access_token")

    def __init__(self, *, entrypoint: str, service_realm: str, client_id: str, client_secret: str) -> None:
        self.entrypoint = entrypoint
        self.service_realm = service_realm
        self.client_id = client_id
        self.client_secret = client_secret

        self._access_token = None

    # TODO: add protection from concurrent calls
    async def get_access_token(self, force: bool) -> str:
        if self._access_token is not None and not force:
            return self._access_token

        url = f"{self.entrypoint}/realms/{self.service_realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with http.client() as client:
            response = await client.post(url, data=data, headers=headers)

            if response.status_code != 200:
                raise CanNotGetAccessToken()

            data = response.json()

            self._access_token = data["access_token"]

            assert self._access_token is not None

            return self._access_token

    async def _call_admin(
        self, method: str, path: str, retry_on_token_loss: bool, data: dict[str, Any] | None = None
    ) -> None:
        access_token = await self.get_access_token(force=False)

        headers = {"Authorization": f"Bearer {access_token}"}

        async with http.client(headers=headers) as client:

            if method in ("POST", "PUT", "PATCH"):
                response = await client.request(method, path, json=data)
            else:
                response = await client.request(method, path)

            if response.status_code in (401, 403) and retry_on_token_loss:
                await self.get_access_token(force=True)
                return await self._call_admin(method, path, retry_on_token_loss=False)

            if response.status_code in (200, 201, 204):
                return

            raise CanNotCallAdminAPI()

    async def remove_user(self, external_user_id: str) -> None:
        url = f"{self.entrypoint}/admin/realms/{self.service_realm}/users/{external_user_id}"
        await self._call_admin("DELETE", url, retry_on_token_loss=True)

    async def revoke_all_user_sessions(self, external_user_id: str) -> None:
        url = f"{self.entrypoint}/admin/realms/{self.service_realm}/users/{external_user_id}/logout"
        await self._call_admin("POST", url, retry_on_token_loss=True)

    async def import_user(self, external_user_id: str, email: str, created_at: datetime.datetime) -> None:
        url = f"{self.entrypoint}/admin/realms/{self.service_realm}/partialImport"

        user = {
            "id": external_user_id,
            "username": email,
            "email": email,
            "emailVerified": True,
            "enabled": True,
            "createdTimestamp": int(created_at.timestamp() * 1000),
        }

        data = {
            "ifResourceExists": "FAIL",  # TODO: we may want to move this to method parameters
            "users": [user],
        }

        await self._call_admin("POST", url, retry_on_token_loss=True, data=data)


def construct(**kwargs: str) -> Plugin:
    return Plugin(
        entrypoint=kwargs["entrypoint"],
        service_realm=kwargs["service_realm"],
        client_id=kwargs["client_id"],
        client_secret=kwargs["client_secret"],
    )
