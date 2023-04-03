
import datetime
import uuid

from ffun.core import api


class Feed(api.Base):
    id: uuid.UUID
    url: str
    loaded_at: datetime.datetime


##################
# Request/Response
##################

class GetFeedsRequest(api.APIRequest):
    pass


class GetFeedsResponse(api.APISuccess):
    feeds: list[Feed]
