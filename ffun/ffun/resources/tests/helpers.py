import datetime
from collections.abc import Mapping

from ffun.domain.entities import UserId
from ffun.resources import domain
from ffun.resources.entities import (
    Resource,
    ResourceReservation,
    ResourceReservationOption,
    ResourceReservationSpecification,
)


async def reserve_resources(
    *,
    limits_by_user: Mapping[UserId, int],
    kind: int,
    interval_started_at: datetime.datetime,
    amount: int,
) -> list[ResourceReservation]:
    reservations = await domain.try_to_reserve_in_order(
        amount=amount,
        options=(ResourceReservationOption(kind=kind, interval_started_at=interval_started_at),),
        specifications=[
            ResourceReservationSpecification(user_id=user_id, limits=(limit,))
            for user_id, limit in limits_by_user.items()
        ],
    )

    assert [reservation.user_id for reservation in reservations] == list(limits_by_user)

    return reservations


async def reserve_resource(
    *,
    user_id: UserId,
    kind: int,
    interval_started_at: datetime.datetime,
    amount: int,
    limit: int,
) -> ResourceReservation:
    reservations = await reserve_resources(
        limits_by_user={user_id: limit},
        kind=kind,
        interval_started_at=interval_started_at,
        amount=amount,
    )

    return reservations[0]


async def consume_resource(
    *,
    user_id: UserId,
    kind: int,
    interval_started_at: datetime.datetime,
    reserved: int,
    used: int | None = None,
    limit: int | None = None,
) -> Resource:
    if used is None:
        used = reserved

    if limit is None:
        limit = reserved

    reservation = await reserve_resource(
        user_id=user_id,
        kind=kind,
        interval_started_at=interval_started_at,
        amount=reserved,
        limit=limit,
    )

    await domain.convert_reserved_to_used([reservation], used=used)

    return await domain.load_resource(
        user_id=user_id,
        kind=kind,
        interval_started_at=interval_started_at,
    )


async def assert_resource_counters(
    *,
    user_id: UserId,
    kind: int,
    interval_started_at: datetime.datetime,
    used: int,
    reserved: int,
) -> Resource:
    history = await domain.load_resource_history(user_id=user_id, kind=kind)
    resources = [resource for resource in history if resource.interval_started_at == interval_started_at]

    assert resources == [
        Resource(
            user_id=user_id,
            kind=kind,
            interval_started_at=interval_started_at,
            used=used,
            reserved=reserved,
        )
    ]

    resource = resources[0]
    assert resource.total == used + reserved

    return resource


async def assert_no_resource_record(
    *,
    user_id: UserId,
    kind: int,
    interval_started_at: datetime.datetime,
) -> None:
    history = await domain.load_resource_history(user_id=user_id, kind=kind)

    assert all(resource.interval_started_at != interval_started_at for resource in history)
