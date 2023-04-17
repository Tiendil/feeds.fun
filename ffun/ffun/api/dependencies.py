from typing import Annotated

import fastapi
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities


async def _user() -> u_entities.User:
    return await u_domain.get_first_user()


user = fastapi.Depends(_user)

User = Annotated[u_entities.User, user]
