import datetime
import enum
import uuid

import pydantic


class Resource(pydantic.BaseModel):
    user_id: uuid.UUID
    kind: int
    interval_started_at: datetime.datetime

    used: int
    reserved: int

    @property
    def total(self):
        return self.used + self.reserved
