import datetime
import uuid

import pydantic


class Resource(pydantic.BaseModel):
    user_id: uuid.UUID
    kind: int
    interval_started_at: datetime.datetime

    used: int
    reserved: int

    @property
    def total(self) -> int:
        return self.used + self.reserved
