import datetime
import uuid

from ffun.core.entities import BaseEntity


class ProcessorPointer(BaseEntity):
    processor_id: int
    pointer_created_at: datetime.datetime
    pointer_entity_id: uuid.UUID
