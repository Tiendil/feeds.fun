from ffun.dispatcher.entities import ProcessorDispatchInfo


def processor_dispatch_info(
    processor_id: int,
    *,
    subqueue_id: int | None = None,
    allowed_for_collections: bool = True,
    allowed_for_users: bool = True,
) -> ProcessorDispatchInfo:
    return ProcessorDispatchInfo(
        processor_id=processor_id,
        subqueue_id=processor_id if subqueue_id is None else subqueue_id,
        allowed_for_collections=allowed_for_collections,
        allowed_for_users=allowed_for_users,
    )
