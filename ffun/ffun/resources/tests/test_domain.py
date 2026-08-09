import datetime

import psycopg
import pytest

from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeNotChanged
from ffun.domain.datetime_intervals import month_interval_start
from ffun.domain.entities import UserId
from ffun.resources import domain, errors, operations
from ffun.resources.domain import load_resource
from ffun.resources.entities import (
    ResourceIdentity,
    ResourceKey,
    ResourceKind,
    ResourceReservation,
    ResourceReservationLimit,
    ResourceReservationOption,
    ResourceReservationSpecification,
)
from ffun.resources.operations import initialize_resources, try_to_reserve
from ffun.resources.tests.helpers import reserve_resources


class TestLoadResources:
    def test_reexports_operation(self) -> None:
        assert domain.load_resources is operations.load_resources


class TestLoadResource:
    @pytest.mark.asyncio
    async def test_initialized(self, internal_user_id: UserId, resource_kind: ResourceKind) -> None:
        interval_started_at = month_interval_start()

        await initialize_resources(
            execute,
            ResourceIdentity.single(
                internal_user_id,
                ResourceKey(kind=resource_kind, interval_started_at=interval_started_at),
            ),
        )

        await try_to_reserve(
            execute,
            user_limits=[ResourceReservationLimit(user_id=internal_user_id, limit=100)],
            kind=resource_kind,
            interval_started_at=interval_started_at,
            amount=13,
        )

        resource = await load_resource(
            user_id=internal_user_id,
            kind=resource_kind,
            interval_started_at=interval_started_at,
        )

        assert resource.user_id == internal_user_id
        assert resource.kind == resource_kind
        assert resource.interval_started_at == interval_started_at
        assert resource.used == 0
        assert resource.reserved == 13

    @pytest.mark.asyncio
    async def test_not_initialized(self, internal_user_id: UserId, resource_kind: int) -> None:
        interval_started_at = month_interval_start()

        resource = await load_resource(
            user_id=internal_user_id,
            kind=resource_kind,
            interval_started_at=interval_started_at,
        )

        assert resource.user_id == internal_user_id
        assert resource.kind == resource_kind
        assert resource.interval_started_at == interval_started_at
        assert resource.used == 0
        assert resource.reserved == 0


class TestLoadResourceStatistics:
    def test_reexports_operation(self) -> None:
        assert domain.load_resource_statistics is domain.operations.load_resource_statistics


class TestBuildUserLimits:
    def test_filters_reserved_users(self, internal_user_id: UserId, another_internal_user_id: UserId) -> None:
        specifications = [
            ResourceReservationSpecification(user_id=internal_user_id, limits=(10,)),
            ResourceReservationSpecification(user_id=another_internal_user_id, limits=(20,)),
        ]

        user_limits = domain._build_user_limits(
            specifications,
            option_index=0,
            reserved_user_ids={internal_user_id},
        )

        assert user_limits == [ResourceReservationLimit(user_id=another_internal_user_id, limit=20)]

    def test_filters_unavailable_options(self, internal_user_id: UserId, another_internal_user_id: UserId) -> None:
        specifications = [
            ResourceReservationSpecification(user_id=internal_user_id, limits=(None,)),
            ResourceReservationSpecification(user_id=another_internal_user_id, limits=(20,)),
        ]

        user_limits = domain._build_user_limits(
            specifications,
            option_index=0,
            reserved_user_ids=set(),
        )

        assert user_limits == [ResourceReservationLimit(user_id=another_internal_user_id, limit=20)]


class TestTryToReserveInOrder:
    @pytest.mark.asyncio
    async def test_one_user_with_one_option(self, internal_user_id: UserId, resource_kind: int) -> None:
        amount = 20
        interval_started_at = month_interval_start()

        reservations = await domain.try_to_reserve_in_order(
            amount=amount,
            options=(
                ResourceReservationOption(
                    kind=resource_kind,
                    interval_started_at=interval_started_at,
                ),
            ),
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    limits=(amount,),
                )
            ],
        )

        resource = await domain.load_resource(
            user_id=internal_user_id,
            kind=resource_kind,
            interval_started_at=interval_started_at,
        )

        assert reservations == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=resource_kind,
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
        resource_kind: int,
        another_resource_kind: int,
    ) -> None:
        amount = 20
        first_interval_started_at = month_interval_start()
        second_interval_started_at = first_interval_started_at + datetime.timedelta(days=1)

        reservations = await domain.try_to_reserve_in_order(
            amount=amount,
            options=(
                ResourceReservationOption(
                    kind=resource_kind,
                    interval_started_at=first_interval_started_at,
                ),
                ResourceReservationOption(
                    kind=another_resource_kind,
                    interval_started_at=second_interval_started_at,
                ),
            ),
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    limits=(amount, amount),
                ),
                ResourceReservationSpecification(
                    user_id=another_internal_user_id,
                    limits=(amount - 1, amount),
                ),
            ],
        )

        assert reservations == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=resource_kind,
                interval_started_at=first_interval_started_at,
                amount=amount,
            ),
            ResourceReservation(
                user_id=another_internal_user_id,
                kind=another_resource_kind,
                interval_started_at=second_interval_started_at,
                amount=amount,
            ),
        ]

        first_resource = await domain.load_resource(
            user_id=internal_user_id,
            kind=resource_kind,
            interval_started_at=first_interval_started_at,
        )
        rejected_resource = await domain.load_resource(
            user_id=another_internal_user_id,
            kind=resource_kind,
            interval_started_at=first_interval_started_at,
        )
        second_resource = await domain.load_resource(
            user_id=another_internal_user_id,
            kind=another_resource_kind,
            interval_started_at=second_interval_started_at,
        )
        skipped_history = await domain.load_resource_history(user_id=internal_user_id, kind=another_resource_kind)

        assert first_resource.reserved == amount
        assert rejected_resource.reserved == 0
        assert second_resource.reserved == amount
        assert skipped_history == []

    @pytest.mark.asyncio
    async def test_all_options_reject(self, internal_user_id: UserId, resource_kind: int) -> None:
        amount = 20
        interval_started_at = month_interval_start()

        reservations = await domain.try_to_reserve_in_order(
            amount=amount,
            options=(
                ResourceReservationOption(
                    kind=resource_kind,
                    interval_started_at=interval_started_at,
                ),
            ),
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    limits=(amount - 1,),
                )
            ],
        )

        resource = await domain.load_resource(
            user_id=internal_user_id,
            kind=resource_kind,
            interval_started_at=interval_started_at,
        )

        assert reservations == []
        assert resource.reserved == 0

    @pytest.mark.asyncio
    async def test_update_failure_rolls_back_initialization(
        self, internal_user_id: UserId, resource_kind: int
    ) -> None:
        too_large_amount = 2**63
        interval_started_at = month_interval_start()

        with pytest.raises(psycopg.errors.NumericValueOutOfRange):  # type: ignore[misc]
            await domain.try_to_reserve_in_order(
                amount=too_large_amount,
                options=(
                    ResourceReservationOption(
                        kind=resource_kind,
                        interval_started_at=interval_started_at,
                    ),
                ),
                specifications=[
                    ResourceReservationSpecification(
                        user_id=internal_user_id,
                        limits=(too_large_amount,),
                    )
                ],
            )

        history = await domain.load_resource_history(user_id=internal_user_id, kind=resource_kind)

        assert history == []

    @pytest.mark.asyncio
    async def test_duplicate_user_specifications_raise_error(
        self, internal_user_id: UserId, resource_kind: int, another_resource_kind: int
    ) -> None:
        first_interval_started_at = month_interval_start()
        second_interval_started_at = first_interval_started_at + datetime.timedelta(days=1)

        with pytest.raises(errors.DuplicateReservationSpecifications):
            await domain.try_to_reserve_in_order(
                amount=20,
                options=(
                    ResourceReservationOption(
                        kind=resource_kind,
                        interval_started_at=first_interval_started_at,
                    ),
                    ResourceReservationOption(
                        kind=another_resource_kind,
                        interval_started_at=second_interval_started_at,
                    ),
                ),
                specifications=[
                    ResourceReservationSpecification(
                        user_id=internal_user_id,
                        limits=(20, None),
                    ),
                    ResourceReservationSpecification(
                        user_id=internal_user_id,
                        limits=(None, 20),
                    ),
                ],
            )

        first_history = await domain.load_resource_history(user_id=internal_user_id, kind=resource_kind)
        duplicate_history = await domain.load_resource_history(user_id=internal_user_id, kind=another_resource_kind)

        assert first_history == []
        assert duplicate_history == []

    @pytest.mark.asyncio
    async def test_skips_unavailable_options(
        self,
        internal_user_id: UserId,
        resource_kind: int,
        another_resource_kind: int,
    ) -> None:
        amount = 20
        first_interval_started_at = month_interval_start()
        second_interval_started_at = first_interval_started_at + datetime.timedelta(days=1)

        reservations = await domain.try_to_reserve_in_order(
            amount=amount,
            options=(
                ResourceReservationOption(
                    kind=resource_kind,
                    interval_started_at=first_interval_started_at,
                ),
                ResourceReservationOption(
                    kind=another_resource_kind,
                    interval_started_at=second_interval_started_at,
                ),
            ),
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    limits=(None, amount),
                ),
            ],
        )

        unavailable_history = await domain.load_resource_history(user_id=internal_user_id, kind=resource_kind)

        assert reservations == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=another_resource_kind,
                interval_started_at=second_interval_started_at,
                amount=amount,
            )
        ]
        assert unavailable_history == []

    @pytest.mark.asyncio
    async def test_rejects_misaligned_limits_before_reserving(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        resource_kind: int,
    ) -> None:
        amount = 20
        interval_started_at = month_interval_start()

        with pytest.raises(errors.ReservationOptionsAndLimitsMismatch):
            await domain.try_to_reserve_in_order(
                amount=amount,
                options=(
                    ResourceReservationOption(
                        kind=resource_kind,
                        interval_started_at=interval_started_at,
                    ),
                ),
                specifications=[
                    ResourceReservationSpecification(
                        user_id=internal_user_id,
                        limits=(amount,),
                    ),
                    ResourceReservationSpecification(
                        user_id=another_internal_user_id,
                        limits=(),
                    ),
                ],
            )

        history = await domain.load_resource_history(user_id=internal_user_id, kind=resource_kind)

        assert history == []

    @pytest.mark.asyncio
    async def test_zero_amount(self, internal_user_id: UserId, resource_kind: int) -> None:
        interval_started_at = month_interval_start()

        reservations = await domain.try_to_reserve_in_order(
            amount=0,
            options=(
                ResourceReservationOption(
                    kind=resource_kind,
                    interval_started_at=interval_started_at,
                ),
            ),
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    limits=(0,),
                )
            ],
        )

        assert reservations == [
            ResourceReservation(
                user_id=internal_user_id,
                kind=resource_kind,
                interval_started_at=interval_started_at,
                amount=0,
            )
        ]

    @pytest.mark.asyncio
    async def test_empty_specifications(self, resource_kind: int) -> None:
        reservations = await domain.try_to_reserve_in_order(
            amount=20,
            options=(
                ResourceReservationOption(
                    kind=resource_kind,
                    interval_started_at=month_interval_start(),
                ),
            ),
            specifications=[],
        )

        assert reservations == []

    @pytest.mark.asyncio
    async def test_empty_options(self, internal_user_id: UserId, resource_kind: int) -> None:
        reservations = await domain.try_to_reserve_in_order(
            amount=20,
            options=(),
            specifications=[
                ResourceReservationSpecification(
                    user_id=internal_user_id,
                    limits=(),
                )
            ],
        )

        history = await domain.load_resource_history(user_id=internal_user_id, kind=resource_kind)

        assert reservations == []
        assert history == []


class TestConvertReservedToUsed:
    @pytest.mark.asyncio
    async def test_empty_reservations(self) -> None:
        async with TableSizeNotChanged("r_resources"):
            await domain.convert_reserved_to_used([], used=20)

    @pytest.mark.asyncio
    async def test_consumes_all_reservations(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        resource_kind: int,
    ) -> None:
        user_ids = [internal_user_id, another_internal_user_id]
        amount = 20
        interval_started_at = month_interval_start()
        reservations = await reserve_resources(
            limits_by_user={user_id: amount for user_id in user_ids},
            kind=resource_kind,
            interval_started_at=interval_started_at,
            amount=amount,
        )

        await domain.convert_reserved_to_used(reservations, used=amount)

        for user_id in user_ids:
            resource = await domain.load_resource(
                user_id=user_id,
                kind=resource_kind,
                interval_started_at=interval_started_at,
            )
            assert resource.used == amount
            assert resource.reserved == 0

    @pytest.mark.asyncio
    async def test_releases_all_reservations(
        self,
        internal_user_id: UserId,
        another_internal_user_id: UserId,
        resource_kind: int,
    ) -> None:
        user_ids = [internal_user_id, another_internal_user_id]
        amount = 20
        interval_started_at = month_interval_start()
        reservations = await reserve_resources(
            limits_by_user={user_id: amount for user_id in user_ids},
            kind=resource_kind,
            interval_started_at=interval_started_at,
            amount=amount,
        )

        await domain.convert_reserved_to_used(reservations, used=0)

        for user_id in user_ids:
            resource = await domain.load_resource(
                user_id=user_id,
                kind=resource_kind,
                interval_started_at=interval_started_at,
            )
            assert resource.used == 0
            assert resource.reserved == 0
