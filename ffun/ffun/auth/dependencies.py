from typing import Annotated

import fastapi
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.usermetadata.asyncio import update_user_metadata

from .settings import AuthMode, settings


async def _supertokens_user(session: SessionContainer = fastapi.Depends(verify_session())) -> u_entities.User:
    return await u_domain.get_or_create_user(u_entities.Service.supertokens, session.user_id)


async def _single_user() -> u_entities.User:
    return await u_domain.get_or_create_user(u_entities.Service.single,
                                             settings.single_user.external_id)


if settings.auth_mode == AuthMode.single_user:
    user = fastapi.Depends(_single_user)
elif settings.auth_mode == AuthMode.supertokens:
    user = fastapi.Depends(_supertokens_user)
else:
    raise NotImplementedError(f"AuthMode {settings.auth_mode} not implemented")


User = Annotated[u_entities.User, user]
