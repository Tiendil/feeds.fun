import datetime
from collections.abc import Collection, Sequence

from ffun.core.postgresql import run_in_transaction, transaction
from ffun.domain.entities import UserId
from ffun.resources import errors, operations
from ffun.resources.entities import (
    Resource,
    ResourceReservation,
    ResourceReservationOption,
    ResourceReservationSpecification,
)

load_resources = operations.load_resources
convert_reserved_to_used = run_in_transaction(operations.convert_reserved_to_used)
load_resource_history = operations.load_resource_history
count_total_resources_per_user = operations.count_total_resources_per_user


async def load_resource(user_id: UserId, kind: int, interval_started_at: datetime.datetime) -> Resource:
    resources = await load_resources([user_id], kind, interval_started_at)
    return resources[user_id]


def _build_user_limits(
    specifications: Sequence[ResourceReservationSpecification],
    option_index: int,
    reserved_user_ids: Collection[UserId],
) -> list[tuple[UserId, int]]:
    user_limits: list[tuple[UserId, int]] = []

    for specification in specifications:
        if specification.user_id in reserved_user_ids:
            continue

        limit = specification.limits[option_index]

        if limit is None:
            continue

        user_limits.append((specification.user_id, limit))

    return user_limits


async def try_to_reserve_in_order(  # noqa: CCR001
    *,
    amount: int,
    options: Sequence[ResourceReservationOption],
    specifications: Sequence[ResourceReservationSpecification],
) -> list[ResourceReservation]:
    for specification in specifications:
        if len(specification.limits) != len(options):
            raise errors.ReservationOptionsAndLimitsMismatch()

    specification_user_ids = [specification.user_id for specification in specifications]

    if len(specification_user_ids) != len(set(specification_user_ids)):
        raise errors.DuplicateReservationSpecifications()

    reservations_by_user_id: dict[UserId, ResourceReservation] = {}

    for option_index, option in enumerate(options):
        user_limits = _build_user_limits(
            specifications,
            option_index,
            reserved_user_ids=reservations_by_user_id,
        )

        if not user_limits:
            continue

        # Options intentionally use separate transactions because resource availability does not require a
        # point-in-time snapshot across options: users who cannot reserve one option can fall back to a later one.
        async with transaction() as execute:
            reservations = await operations.try_to_reserve(
                execute,
                user_limits=user_limits,
                kind=option.kind,
                interval_started_at=option.interval_started_at,
                amount=amount,
            )

        for reservation in reservations:
            reservations_by_user_id[reservation.user_id] = reservation

    return [
        reservations_by_user_id[specification.user_id]
        for specification in specifications
        if specification.user_id in reservations_by_user_id
    ]
