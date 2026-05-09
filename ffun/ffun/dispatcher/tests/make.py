from collections.abc import Sequence

from ffun.dispatcher.entities import ProcessorDispatchInfo, ProcessorDispatchRoute
from ffun.domain.entities import ProcessorId
from ffun.llms_framework.entities import LLMApiKeyType


def processor_dispatch_route(
    *,
    allowed_for_collections: bool = True,
    allowed_for_users: bool = True,
    llm_api_key_type: LLMApiKeyType | None = None,
) -> ProcessorDispatchRoute:
    return ProcessorDispatchRoute(
        allowed_for_collections=allowed_for_collections,
        allowed_for_users=allowed_for_users,
        llm_api_key_type=llm_api_key_type,
    )


def processor_dispatch_routes(
    *,
    allowed_for_collections: bool | None = None,
    allowed_for_users: bool | None = None,
    routes: Sequence[ProcessorDispatchRoute] | None = None,
) -> tuple[ProcessorDispatchRoute, ...]:
    if routes is not None:
        if allowed_for_collections is not None or allowed_for_users is not None:
            raise ValueError("Pass either routes or allowed flags, not both")

        return tuple(routes)

    return (
        processor_dispatch_route(
            allowed_for_collections=True if allowed_for_collections is None else allowed_for_collections,
            allowed_for_users=True if allowed_for_users is None else allowed_for_users,
        ),
    )


def processor_dispatch_info(
    processor_id: int,
    *,
    subqueue_id: int | None = None,
    allowed_for_collections: bool | None = None,
    allowed_for_users: bool | None = None,
    routes: Sequence[ProcessorDispatchRoute] | None = None,
) -> ProcessorDispatchInfo:
    return ProcessorDispatchInfo(
        processor_id=ProcessorId(processor_id),
        subqueue_id=ProcessorId(processor_id if subqueue_id is None else subqueue_id),
        routes=processor_dispatch_routes(
            allowed_for_collections=allowed_for_collections,
            allowed_for_users=allowed_for_users,
            routes=routes,
        ),
    )
