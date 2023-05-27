from typing import Annotated

import fastapi
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.usermetadata.asyncio import update_user_metadata


async def _user(session: SessionContainer = fastapi.Depends(verify_session())) -> u_entities.User:
    return await u_domain.get_or_create_user(u_entities.Service.supertokens, session.user_id)


user = fastapi.Depends(_user)

User = Annotated[u_entities.User, user]
