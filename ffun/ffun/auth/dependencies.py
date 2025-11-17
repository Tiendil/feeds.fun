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

    # external_user_id must has a value, None or empty string is not allowed
    if not external_user_id:
        raise errors.IdPNoUserIdHeader()

    # determine identity_provider_id

    if settings.force_external_identity_provider_id is not None:
        identity_provider_id = settings.force_external_identity_provider_id
    else:
        identity_provider_id = request.headers.get(settings.header_identity_provider_id)

    # identity_provider_id must has a value, None or empty string is not allowed
    if not identity_provider_id:
        raise errors.IdPNoIdentityProviderIdHeader()

    # determine internal IdP service id

    idp = settings.get_idp_by_external_id(identity_provider_id)

    if idp is None:
        raise errors.IdPNoIdentityProviderInSettings()

    return await u_domain.get_or_create_user(idp.internal_id, external_user_id)


# NOTE: we do not need "optional user" dependency
#       because auth proxies have trouble with handling optional authentication for the endpoints.
#       => we duplicate some API endpoints to have both authenticated and unauthenticated versions.
#          SPA routes requests to the appropriate endpoint.

user = fastapi.Depends(_idp_user)

User = Annotated[u_entities.User, user]
