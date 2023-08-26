from typing import Annotated

import fastapi
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from ffun.auth.settings import AuthMode, settings
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities


async def _supertokens_user(session: SessionContainer = fastapi.Depends(verify_session())) -> u_entities.User:
    return await u_domain.get_or_create_user(u_entities.Service.supertokens, session.user_id)


async def _single_user() -> u_entities.User:
    return await u_domain.get_or_create_user(u_entities.Service.single, settings.single_user.external_id)


if settings.mode == AuthMode.single_user:
    user = fastapi.Depends(_single_user)
elif settings.mode == AuthMode.supertokens:
    user = fastapi.Depends(_supertokens_user)
else:
    raise NotImplementedError(f"AuthMode {settings.mode} not implemented")


User = Annotated[u_entities.User, user]
