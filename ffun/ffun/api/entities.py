
import datetime
import uuid

from ffun.core import api
from ffun.feeds import entities as f_entities


class Feed(api.Base):
    id: uuid.UUID
    url: str
    loadedAt: datetime.datetime

    @classmethod
    def from_internal(cls, feed: f_entities.Feed) -> 'Feed':
        return cls(
            id=feed.id,
            url=feed.url,
            loadedAt=feed.loaded_at,
        )


##################
# Request/Response
##################

class GetFeedsRequest(api.APIRequest):
    pass


class GetFeedsResponse(api.APISuccess):
    feeds: list[Feed]
