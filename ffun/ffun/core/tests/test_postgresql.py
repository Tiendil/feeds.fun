from typing import cast

import pytest
from pytest_mock import MockerFixture

from ffun.core import postgresql


class TestExecutor:
    @pytest.mark.asyncio
    async def test_pool_not_initialized(self, mocker: MockerFixture) -> None:
        mocker.patch.object(postgresql, "POOL", None)

        with pytest.raises(RuntimeError, match="POOL MUST be initialized"):
            async with postgresql._executor(autocommit=False):
                pass

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("autocommit", "same_transaction"),
        [(False, True), (True, False)],
    )
    async def test_uses_requested_transaction_mode(self, autocommit: bool, same_transaction: bool) -> None:
        async with postgresql._executor(autocommit=autocommit) as execute:
            first = cast(int, (await execute("SELECT txid_current() AS transaction_id"))[0]["transaction_id"])
            second = cast(int, (await execute("SELECT txid_current() AS transaction_id"))[0]["transaction_id"])

        assert (first == second) == same_transaction
