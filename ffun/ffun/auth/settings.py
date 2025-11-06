from typing import Any

import pydantic
import pydantic_settings

from ffun.auth.idps.plugin import Plugin
from ffun.core import utils
from ffun.core.settings import BaseSettings
from ffun.domain.entities import IdPId

#################################
# default values for services
# used to simplify unit tests
#################################
primary_oidc_service = "primary_oidc"
single_user_service = "single_user"

primary_oidc_service_id = IdPId(1)
single_user_service_id = IdPId(2)
#################################


class IdP(BaseSettings):
    # id that service receives from the infrastructure
    external_id: str

    # id that we store in the database and use internally
    internal_id: IdPId

    # IdP plugin used to support extended functionality
    # like removing users, logging user out from all sessions, etc.
    plugin: Plugin

    # additional configs for the identity provider plugin, passed as is to the plugin constructor
    extras: dict[str, str] = pydantic.Field(default_factory=dict)

    # @pydantic.field_validator('plugin', mode='before')
    @pydantic.model_validator(mode="before")
    @classmethod
    def build_plugin(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        v = data.get("plugin")

        if not isinstance(v, str):
            raise ValueError("plugin must be defined as a string module.path:callable_constructor")

        extras = data.get("extras", {}) or {}

        try:
            constructor = utils.import_from_string(v)
        except Exception as e:
            raise ValueError(f"Cannot import '{v}': {e}") from e

        try:
            data["plugin"] = constructor(**extras)  # type: ignore
        except Exception as e:
            raise ValueError(f"Cannot construct plugin from '{v}': {e}") from e

        return data


class Settings(BaseSettings):
    # force_* settings may be used for:
    #
    # - turning on single user mode
    # - debugging
    # - testing
    #
    # Because of security implications, they are forced to be None by default.
    # For testing, these settings should be overridden in fixtures nearest to tests.
    # i.e., most of the code should be tested without these settings set.
    force_external_user_id: str | None = None
    # Most likely, you may want to set this up to the value of the single_user service_id
    force_external_identity_provider_id: str | None = None

    header_user_id: str = "X-FFun-User-Id"
    header_identity_provider_id: str = "X-FFun-Identity-Provider-Id"

    idps: list[IdP] = pydantic.Field(
        default_factory=lambda: [
            # keycloak config for the dev environment
            IdP(
                external_id=primary_oidc_service,
                internal_id=primary_oidc_service_id,
                plugin="ffun.auth.idps.keycloak:construct",  # type: ignore
                extras={
                    "entrypoint": "http://idp:8080",
                    "service_realm": "dev",
                    "client_id": "backend-client",
                    "client_secret": "b6f2e5a6-d536-405b-b8ab-04df432ed091",
                },
            ),
            IdP(
                external_id=single_user_service,
                internal_id=single_user_service_id,
                plugin="ffun.auth.idps.no_idp:construct",  # type: ignore
            ),
        ]
    )

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_AUTH_")

    @property
    def is_single_user_mode(self) -> bool:
        return self.force_external_user_id is not None

    def get_idp_by_external_id(self, external_id: str) -> IdP | None:
        for idp in self.idps:
            if idp.external_id == external_id:
                return idp

        return None

    def get_idp_by_internal_id(self, internal_id: IdPId) -> IdP | None:
        for idp in self.idps:
            if idp.internal_id == internal_id:
                return idp

        return None


settings = Settings()
