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
    __slots__ = ("entrypoint", "service_realm", "admin_realm", "client_id", "client_secret", "_access_token")

    def __init__(
        self, *, entrypoint: str, service_realm: str, admin_realm: str, client_id: str, client_secret: str
    ) -> None:
        self.entrypoint = entrypoint
        self.service_realm = service_realm
        self.admin_realm = admin_realm
        self.client_id = client_id
        self.client_secret = client_secret

        self._access_token = None

    # TODO: add protection from concurrent calls
    async def get_access_token(self) -> str:
        if self._access_token is not None:
            return self._access_token

        url = f"{self.entrypoint}/realms/{self.admin_realm}/protocol/openid-connect/token"

        headers = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with http.client(headers=headers) as client:
            response = await client.post(url)

            if response.status != 200:
                raise CanNotGetAccessToken()

            data = await response.json()

            self._access_token = data["access_token"]

            return self._access_token

    async def _call_admin(self, method: str, path: str) -> None:
        access_token = await self.get_access_token()

        headers = {"Authorization": f"Bearer {access_token}"}

        async with http.client(headers=headers) as client:
            response = await client.request(method, path)

            if response.status != 200:
                raise CanNotCallAdminAPI()

    async def remove_user(self, external_user_id: str) -> None:
        url = f"{self.entrypoint}/admin/realms/{self.service_realm}/users/{external_user_id}"
        await self._call_admin("DELETE", url)

    async def revoke_all_user_sessions(self, external_user_id: str) -> None:
        url = f"{self.entrypoint}/admin/realms/{self.service_realm}/users/{external_user_id}/logout"
        await self._call_admin("POST", url)


def construct(**kwargs: object) -> Plugin:
    return Plugin(**kwargs)
