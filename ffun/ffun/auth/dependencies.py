from typing import Annotated

import fastapi
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from ffun.auth.settings import AuthMode, settings
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities

# ATTENTION: We check the database in supertokens sessions to be able to logout user from backend from all sessions.
#            It is the fastest and easiest way to do it, and it should not cause performance issues, at least for now.
#            In the future, we may want to improve user experience by removing this check and
#            implementing faster custom logout
# TODO: implement something like that for OIDC


async def _supertokens_user(
    session: SessionContainer = fastapi.Depends(verify_session(check_database=True)),
) -> u_entities.User:
    return await u_domain.get_or_create_user(u_entities.Service.supertokens, session.user_id)


async def _supertokens_optional_user(
    session: SessionContainer = fastapi.Depends(verify_session(check_database=True, session_required=False)),
) -> u_entities.User | None:
    if session is None:
        return None

    return await u_domain.get_or_create_user(u_entities.Service.supertokens, session.user_id)


async def _single_user() -> u_entities.User:
    return await u_domain.get_or_create_user(u_entities.Service.single, settings.single_user.external_id)


async def _oidc_user(request: fastapi.Request) -> u_entities.User:
    external_user_id = request.headers.get(settings.oidc.header_user_id)
    identity_provider_id = request.headers.get(settings.oidc.header_identity_provider_id)

    if external_user_id is None:
        # TODO: better error handling
        raise NotImplementedError("OIDC user ID header not found")

    if identity_provider_id is not None:
        # TODO: better error handling
        raise NotImplementedError("OIDC identity provider ID handling not implemented")

    return await u_domain.get_or_create_user(getattr(u_entities.Service, identity_provider_id), external_user_id)


async def _oidc_optional_user(request: fastapi.Request) -> u_entities.User | None:
    if settings.oidc.header_user_id not in request.headers:
        return None

    return await _oidc_user(request)


if settings.mode == AuthMode.single_user:
    user = fastapi.Depends(_single_user)
    optional_user = fastapi.Depends(_single_user)
elif settings.mode == AuthMode.supertokens:
    user = fastapi.Depends(_supertokens_user)
    optional_user = fastapi.Depends(_supertokens_optional_user)
elif settings.mode == AuthMode.oidc:
    user = fastapi.Depends(_oidc_user)
    optional_user = fastapi.Depends(_oidc_optional_user)
else:
    raise NotImplementedError(f"AuthMode {settings.mode} not implemented")


User = Annotated[u_entities.User, user]

OptionalUser = Annotated[u_entities.User | None, optional_user]
