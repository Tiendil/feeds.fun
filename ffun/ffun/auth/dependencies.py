from typing import Annotated

import fastapi

from ffun.auth import errors
from ffun.auth.settings import AuthMode, settings
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities


async def _single_user() -> u_entities.User:
    return await u_domain.get_or_create_user(settings.auth_service_map['single_user'],
                                             settings.single_user.external_id)


async def _oidc_user(request: fastapi.Request) -> u_entities.User:
    external_user_id = request.headers.get(settings.oidc.header_user_id)
    identity_provider_id = request.headers.get(settings.oidc.header_identity_provider_id)

    if external_user_id is None:
        raise errors.OIDCNoUserIdHerader()

    if identity_provider_id is None:
        raise errors.OIDCNoIdentityProviderIdHeader()

    if identity_provider_id not in settings.auth_service_map:
        raise errors.OIDCNoIdentityProviderInSettings()

    service_id = settings.auth_service_map[identity_provider_id]

    return await u_domain.get_or_create_user(service_id, external_user_id)


async def _oidc_optional_user(request: fastapi.Request) -> u_entities.User | None:
    if settings.oidc.header_user_id not in request.headers:
        return None

    return await _oidc_user(request)


if settings.mode == AuthMode.single_user:
    user = fastapi.Depends(_single_user)
    optional_user = fastapi.Depends(_single_user)
elif settings.mode == AuthMode.oidc:
    user = fastapi.Depends(_oidc_user)
    optional_user = fastapi.Depends(_oidc_optional_user)
else:
    raise NotImplementedError(f"AuthMode {settings.mode} not implemented")


User = Annotated[u_entities.User, user]

OptionalUser = Annotated[u_entities.User | None, optional_user]
