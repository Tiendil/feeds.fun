import datetime

from ffun.domain.entities import UserId
from ffun.product.entities import Resource as AppResource
from ffun.resources import domain as r_domain
from ffun.resources import entities as r_entities


async def reserve_resource(
    user_id: UserId,
    interval_started_at: datetime.datetime,
    amount: int,
    limit: int,
) -> None:
    reservations = await r_domain.try_to_reserve_in_order(
        specifications=[
            r_entities.ResourceReservationSpecification(
                user_id=user_id,
                amount=amount,
                options=(
                    r_entities.ResourceReservationOption(
                        kind=AppResource.tokens_cost,
                        interval_started_at=interval_started_at,
                        limit=limit,
                    ),
                ),
            )
        ],
    )
    assert [reservation.user_id for reservation in reservations] == [user_id]
