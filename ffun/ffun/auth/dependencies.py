from typing import Annotated

import fastapi

from ffun.auth import errors
from ffun.auth.settings import settings
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities


async def _idp_user(request: fastapi.Request) -> u_entities.User:
    external_user_id: str | None
    identity_provider_id: str | None

    # determine external_user_id

    if settings.force_external_user_id is not None:
        external_user_id = settings.force_external_user_id
    else:
        external_user_id = request.headers.get(settings.header_user_id)

    if external_user_id is None:
        raise errors.IdPNoUserIdHerader()

    # determine identity_provider_id

    if settings.force_external_identity_provider_id is not None:
        identity_provider_id = settings.force_external_identity_provider_id
    else:
        identity_provider_id = request.headers.get(settings.header_identity_provider_id)

    if identity_provider_id is None:
        raise errors.IdPNoIdentityProviderIdHeader()

    # determine internal IdP service id

    idp = settings.get_idp_by_external_id(identity_provider_id)

    if idp is None:
        raise errors.IdPNoIdentityProviderInSettings()

    return await u_domain.get_or_create_user(idp.internal_id, external_user_id)


async def _idp_optional_user(request: fastapi.Request) -> u_entities.User | None:
    try:
        return await _idp_user(request)
    except errors.IdPNoUserIdHerader:
        return None


user = fastapi.Depends(_idp_user)
optional_user = fastapi.Depends(_idp_optional_user)


User = Annotated[u_entities.User, user]

OptionalUser = Annotated[u_entities.User | None, optional_user]
