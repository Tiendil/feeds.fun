import datetime
from typing import Iterable

from ffun.domain.entities import UserId
from ffun.resources import operations
from ffun.resources.entities import Resource, ResourceReservation, ResourceReservationSpecification

load_resources = operations.load_resources
convert_reserved_to_used = operations.convert_reserved_to_used
load_resource_history = operations.load_resource_history
count_total_resources_per_user = operations.count_total_resources_per_user


async def load_resource(user_id: UserId, kind: int, interval_started_at: datetime.datetime) -> Resource:
    resources = await load_resources([user_id], kind, interval_started_at)
    return resources[user_id]


async def try_to_reserve_in_order(  # noqa: CCR001
    specifications: Iterable[ResourceReservationSpecification],
) -> list[ResourceReservation]:
    seen_user_ids: set[UserId] = set()
    reservations: list[ResourceReservation] = []

    for specification in specifications:
        if specification.user_id in seen_user_ids:
            continue

        seen_user_ids.add(specification.user_id)

        for option in specification.options:
            if not await operations.try_to_reserve(
                user_id=specification.user_id,
                kind=option.kind,
                interval_started_at=option.interval_started_at,
                amount=specification.amount,
                limit=option.limit,
            ):
                continue

            reservations.append(
                ResourceReservation(
                    user_id=specification.user_id,
                    kind=option.kind,
                    interval_started_at=option.interval_started_at,
                    amount=specification.amount,
                )
            )
            break

    return reservations
