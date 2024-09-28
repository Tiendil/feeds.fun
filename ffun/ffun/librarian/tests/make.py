import uuid

from ffun.core import utils
from ffun.core.postgresql import execute
from ffun.domain.entities import EntryId
from ffun.librarian import operations
from ffun.librarian.entities import ProcessorPointer


async def end_processor_pointer(processor_id: int) -> ProcessorPointer:
    await operations.get_or_create_pointer(processor_id=processor_id)

    next_pointer = ProcessorPointer(
        processor_id=processor_id, pointer_created_at=utils.now(), pointer_entry_id=EntryId(uuid.UUID(int=0))
    )

    await operations.save_pointer(execute, pointer=next_pointer)

    return next_pointer
