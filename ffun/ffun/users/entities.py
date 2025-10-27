import enum

import pydantic

from ffun.domain.entities import UserId


# TODO: these whole enum must be moved to settings
class Service(int, enum.Enum):
    supertokens = 1
    single = 2
    keycloak = 3


class User(pydantic.BaseModel):
    id: UserId
