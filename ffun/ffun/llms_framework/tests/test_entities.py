import decimal

from ffun.core import utils
from ffun.llms_framework.entities import APIKeyUsage, LLMApiKey, LLMProvider, LLMTokens, USDCost


class TestAPIKeyUsage:

    def test_spent_tokens__setuped(self) -> None:
        usage = APIKeyUsage(
            provider=LLMProvider.test,
            user_id=None,
            api_key=LLMApiKey("api_key"),
            reserved_cost=USDCost(decimal.Decimal(123)),
            used_cost=USDCost(decimal.Decimal(17)),
            input_tokens=LLMTokens(100),
            output_tokens=LLMTokens(200),
            interval_started_at=utils.now(),
        )

        assert usage.cost_to_register() == 17

    def test_spent_tokens__not_setuped(self) -> None:
        usage = APIKeyUsage(
            provider=LLMProvider.test,
            user_id=None,
            api_key=LLMApiKey("api_key"),
            reserved_cost=USDCost(decimal.Decimal(132)),
            used_cost=None,
            input_tokens=LLMTokens(100),
            output_tokens=LLMTokens(200),
            interval_started_at=utils.now(),
        )

        assert usage.cost_to_register() == 132
