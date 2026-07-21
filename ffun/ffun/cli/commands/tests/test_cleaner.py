import contextlib

import pytest
from pytest_mock import MockerFixture

from ffun.cli.commands import cleaner


class TestRunClean:
    @pytest.mark.asyncio
    async def test_cleans_expired_entitlements_after_orphaned_data(self, mocker: MockerFixture) -> None:
        mocker.patch.object(cleaner, "with_app", return_value=contextlib.nullcontext())
        logger_info = mocker.patch.object(cleaner.logger, "info")

        operations: list[str] = []

        async def clean_entries(*, chunk: int) -> int:
            assert chunk == 17
            operations.append("entries")
            return 0

        async def clean_feeds(*, chunk: int) -> int:
            assert chunk == 17
            operations.append("feeds")
            return 0

        async def clean_tags(*, chunk: int) -> int:
            assert chunk == 17
            operations.append("tags")
            return 0

        async def clean_entitlements() -> int:
            operations.append("entitlements")
            return 3

        mocker.patch.object(cleaner.m_domain, "clean_orphaned_entries", side_effect=clean_entries)
        mocker.patch.object(cleaner.m_domain, "clean_orphaned_feeds", side_effect=clean_feeds)
        mocker.patch.object(cleaner.m_domain, "clean_orphaned_tags", side_effect=clean_tags)
        mocker.patch.object(cleaner.e_domain, "cleanup_expired_entitlements", side_effect=clean_entitlements)

        await cleaner.run_clean(chunk=17)

        assert operations == ["entries", "feeds", "tags", "entitlements"]
        logger_info.assert_any_call("cleaning_expired_entitlements_finished", deleted=3)
