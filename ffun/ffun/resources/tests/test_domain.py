import datetime

import pytest

from ffun.domain.datetime_intervals import month_interval_start
from ffun.domain.entities import UserId
from ffun.resources import domain
from ffun.resources.domain import load_resource
from ffun.resources.entities import (
    ResourceReservation,
    ResourceReservationOption,
    ResourceReservationSpecification,
)
from ffun.resources.operations import initialize_resource, try_to_reserve


@pytest.fixture  # type: ignore
def kind() -> int:
    return 214


@pytest.fixture  # type: ignore
def another_kind() -> int:
    return 215


class TestLoadResource:
    @pytest.mark.asyncio
    async def test_initialized(self, internal_user_id: UserId, kind: int) -> None:
        interval_started_at = month_interval_start()

        await initialize_resource(user_id=internal_user_id, kind=kind, interval_started_at=interval_started_at)

        await try_to_reserve(
            user_id=internal_user_id, kind=kind, interval_started_at=interval_started_at, amount=13, limit=100
        )

        resource = await load_resource(user_id=internal_user_id, kind=kind, interval_started_at=interval_started_at)

        assert resource.user_id == internal_user_id
        assert resource.kind == kind
        assert resource.interval_started_at == interval_started_at
        assert resource.used == 0
        assert resource.reserved == 13

    @pytest.mark.asyncio
    async def test_not_initialized(self, internal_user_id: UserId, kind: int) -> None:
        interval_started_at = month_interval_start()

        resource = await load_resource(user_id=internal_user_id, kind=kind, interval_started_at=interval_started_at)

        assert resource.user_id == internal_user_id
        assert resource.kind == kind
        assert resource.interval_started_at == interval_started_at
        assert resource.used == 0
        assert resource.reserved == 0


class TestTryToReserveInOrder:
    @pytest.mark.asyncio
    async def test_one_user_with_one_option(self, internal_user_id: UserId, kind: int) -> None:
        amount = 20
        interval_started_at = month_interval_start()

        reservations = await domain.try_to_reserve_in_order(
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    amount=amount,
                    options=(
                        ResourceReservationOption(
                            kind=kind,
                            interval_started_at=interval_started_at,
                            limit=amount,
                        ),
                    ),
                )
            ]
        )

        resource = await domain.load_resource(
            user_id=internal_user_id,
            kind=kind,
            interval_started_at=interval_started_at,
        )

        assert reservations == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=kind,
                interval_started_at=interval_started_at,
                amount=amount,
            )
        ]
        assert resource.reserved == amount

    @pytest.mark.asyncio
    async def test_tries_each_users_options_in_order(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        kind: int,
        another_kind: int,
    ) -> None:
        first_amount = 20
        second_amount = 30
        first_interval_started_at = month_interval_start()
        second_interval_started_at = first_interval_started_at + datetime.timedelta(days=1)

        reservations = await domain.try_to_reserve_in_order(
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    amount=first_amount,
                    options=(
                        ResourceReservationOption(
                            kind=kind,
                            interval_started_at=first_interval_started_at,
                            limit=first_amount,
                        ),
                        ResourceReservationOption(
                            kind=another_kind,
                            interval_started_at=second_interval_started_at,
                            limit=first_amount,
                        ),
                    ),
                ),
                ResourceReservationSpecification(
                    user_id=another_internal_user_id,
                    amount=second_amount,
                    options=(
                        ResourceReservationOption(
                            kind=kind,
                            interval_started_at=first_interval_started_at,
                            limit=second_amount - 1,
                        ),
                        ResourceReservationOption(
                            kind=another_kind,
                            interval_started_at=second_interval_started_at,
                            limit=second_amount,
                        ),
                    ),
                ),
            ],
        )

        assert reservations == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=kind,
                interval_started_at=first_interval_started_at,
                amount=first_amount,
            ),
            ResourceReservation(
                user_id=another_internal_user_id,
                kind=another_kind,
                interval_started_at=second_interval_started_at,
                amount=second_amount,
            ),
        ]

        first_resource = await domain.load_resource(
            user_id=internal_user_id,
            kind=kind,
            interval_started_at=first_interval_started_at,
        )
        rejected_resource = await domain.load_resource(
            user_id=another_internal_user_id,
            kind=kind,
            interval_started_at=first_interval_started_at,
        )
        second_resource = await domain.load_resource(
            user_id=another_internal_user_id,
            kind=another_kind,
            interval_started_at=second_interval_started_at,
        )
        skipped_history = await domain.load_resource_history(user_id=internal_user_id, kind=another_kind)

        assert first_resource.reserved == first_amount
        assert rejected_resource.reserved == 0
        assert second_resource.reserved == second_amount
        assert skipped_history == []

    @pytest.mark.asyncio
    async def test_all_options_reject(self, internal_user_id: UserId, kind: int) -> None:
        amount = 20
        interval_started_at = month_interval_start()

        reservations = await domain.try_to_reserve_in_order(
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    amount=amount,
                    options=(
                        ResourceReservationOption(
                            kind=kind,
                            interval_started_at=interval_started_at,
                            limit=amount - 1,
                        ),
                    ),
                )
            ],
        )

        resource = await domain.load_resource(
            user_id=internal_user_id,
            kind=kind,
            interval_started_at=interval_started_at,
        )

        assert reservations == []
        assert resource.reserved == 0

    @pytest.mark.asyncio
    async def test_deduplicates_user_specifications(
        self, internal_user_id: UserId, kind: int, another_kind: int
    ) -> None:
        first_interval_started_at = month_interval_start()
        second_interval_started_at = first_interval_started_at + datetime.timedelta(days=1)

        reservations = await domain.try_to_reserve_in_order(
            specifications=(
                specification
                for specification in [
                    ResourceReservationSpecification(
                        user_id=internal_user_id,
                        amount=20,
                        options=(
                            ResourceReservationOption(
                                kind=kind,
                                interval_started_at=first_interval_started_at,
                                limit=20,
                            ),
                        ),
                    ),
                    ResourceReservationSpecification(
                        user_id=internal_user_id,
                        amount=30,
                        options=(
                            ResourceReservationOption(
                                kind=another_kind,
                                interval_started_at=second_interval_started_at,
                                limit=30,
                            ),
                        ),
                    ),
                ]
            ),
        )

        resource = await domain.load_resource(
            user_id=internal_user_id,
            kind=kind,
            interval_started_at=first_interval_started_at,
        )
        duplicate_history = await domain.load_resource_history(user_id=internal_user_id, kind=another_kind)

        assert reservations == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=kind,
                interval_started_at=first_interval_started_at,
                amount=20,
            )
        ]
        assert resource.reserved == 20
        assert duplicate_history == []

    @pytest.mark.asyncio
    async def test_zero_amount(self, internal_user_id: UserId, kind: int) -> None:
        interval_started_at = month_interval_start()

        reservations = await domain.try_to_reserve_in_order(
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    amount=0,
                    options=(
                        ResourceReservationOption(
                            kind=kind,
                            interval_started_at=interval_started_at,
                            limit=0,
                        ),
                    ),
                )
            ],
        )

        assert reservations == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=kind,
                interval_started_at=interval_started_at,
                amount=0,
            )
        ]

    @pytest.mark.asyncio
    async def test_empty_specifications(self) -> None:
        reservations = await domain.try_to_reserve_in_order(specifications=[])

        assert reservations == []

    @pytest.mark.asyncio
    async def test_empty_options(self, internal_user_id: UserId, kind: int) -> None:
        reservations = await domain.try_to_reserve_in_order(
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    amount=20,
                    options=(),
                )
            ],
        )

        history = await domain.load_resource_history(user_id=internal_user_id, kind=kind)

        assert reservations == []
        assert history == []
