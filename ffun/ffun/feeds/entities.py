import datetime
import enum
import uuid

import pydantic


class FeedState(int, enum.Enum):
    not_loaded = 1
    loaded = 2
    damaged = 3


class FeedError(int, enum.Enum):
    network_unknown = 1000

    parsing_unknown = 2000
    parsing_encoding_error = 2001
    parsing_format_error = 2002


class Feed(pydantic.BaseModel):
    id: uuid.UUID
    url: str
    state: FeedState = FeedState.not_loaded
    last_error: FeedError|None = None
    load_attempted_at: datetime.datetime|None = None
    loaded_at: datetime.datetime|None = None
