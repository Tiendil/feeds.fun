from __future__ import annotations

from ffun.auth.idps.plugin import Plugin as PluginBase
from ffun.core import errors
from ffun.domain import http


class Error(errors.Error):
    pass


class CanNotCallKratos(Error):
    pass


class CanNotCallHydra(Error):
    pass


class Plugin(PluginBase):
    __slots__ = ("kratos_admin", "hydra_admin")

    def __init__(self, *, kratos_admin: str, hydra_admin: str | None = None) -> None:
        self.kratos_admin = kratos_admin.rstrip("/")
        self.hydra_admin = hydra_admin.rstrip("/") if hydra_admin else None

    async def _hydra_delete(self, path: str, *, expected: set[int]) -> None:
        if not self.hydra_admin:
            return

        url = f"{self.hydra_admin}{path}"

        async with http.client() as client:
            response = await client.delete(url)

        if response.status_code not in expected:
            raise CanNotCallHydra()

    async def _kratos_request(self, method: str, path: str, *, expected: set[int]) -> None:
        url = f"{self.kratos_admin}{path}"

        async with http.client() as client:
            response = await client.request(method, url)

        if response.status_code not in expected:
            raise CanNotCallKratos()

    async def remove_user(self, external_user_id: str) -> None:
        await self._kratos_request("DELETE", f"/identities/{external_user_id}", expected={200, 204, 404})

        await self._hydra_delete(
            f"/oauth2/auth/sessions/login?subject={external_user_id}",
            expected={200, 204, 404},
        )

        await self._hydra_delete(
            f"/oauth2/auth/sessions/consent?subject={external_user_id}",
            expected={200, 204, 404},
        )

    async def revoke_all_user_sessions(self, external_user_id: str) -> None:
        await self._kratos_request(
            "DELETE",
            f"/identities/{external_user_id}/sessions",
            expected={200, 204, 404},
        )

        await self._hydra_delete(
            f"/oauth2/auth/sessions/login?subject={external_user_id}",
            expected={200, 204, 404},
        )

        await self._hydra_delete(
            f"/oauth2/auth/sessions/consent?subject={external_user_id}",
            expected={200, 204, 404},
        )


def construct(**kwargs: str) -> Plugin:
    return Plugin(
        kratos_admin=kwargs["kratos_admin"],
        hydra_admin=kwargs.get("hydra_admin"),
    )
