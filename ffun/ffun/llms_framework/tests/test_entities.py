from ffun.core import utils
from ffun.llms_framework.entities import APIKeyUsage, LLMApiKey


class TestAPIKeyUsage:

    def test_spent_tokens__setuped(self) -> None:
        usage = APIKeyUsage(
            user_id=None,
            api_key=LLMApiKey("api_key"),
            reserved_tokens=100,
            used_tokens=10,
            interval_started_at=utils.now(),
        )

        assert usage.spent_tokens() == 10

    def test_spent_tokens__not_setuped(self) -> None:
        usage = APIKeyUsage(
            user_id=None,
            api_key=LLMApiKey("api_key"),
            reserved_tokens=100,
            used_tokens=None,
            interval_started_at=utils.now(),
        )

        assert usage.spent_tokens() == 100
