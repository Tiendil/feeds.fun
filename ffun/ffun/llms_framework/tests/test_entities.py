import decimal

from ffun.core import utils
from ffun.llms_framework.entities import APIKeyUsage, LLMApiKey, LLMProvider, LLMTokens, ModelInfo, USDCost


class TestModelInfo:

    def test_tokens_cost(self) -> None:
        model = ModelInfo(
            provider=LLMProvider.test,
            name="test-model",
            max_context_size=LLMTokens(1000),
            max_return_tokens=LLMTokens(500),
            input_1m_tokens_cost=USDCost(decimal.Decimal("2.5")),
            output_1m_tokens_cost=USDCost(decimal.Decimal("10")),
        )

        assert model.tokens_cost(input_tokens=LLMTokens(300), output_tokens=LLMTokens(20)) == decimal.Decimal(
            "0.00095"
        )

    def test_max_request_cost(self) -> None:
        model = ModelInfo(
            provider=LLMProvider.test,
            name="test-model",
            max_context_size=LLMTokens(1000),
            max_return_tokens=LLMTokens(500),
            input_1m_tokens_cost=USDCost(decimal.Decimal("2.5")),
            output_1m_tokens_cost=USDCost(decimal.Decimal("10")),
        )

        assert model.max_request_cost == decimal.Decimal("0.0075")


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

    def test_spent_tokens__zero_used_cost(self) -> None:
        usage = APIKeyUsage(
            provider=LLMProvider.test,
            user_id=None,
            api_key=LLMApiKey("api_key"),
            reserved_cost=USDCost(decimal.Decimal(132)),
            used_cost=USDCost(decimal.Decimal(0)),
            input_tokens=LLMTokens(100),
            output_tokens=LLMTokens(200),
            interval_started_at=utils.now(),
        )

        assert usage.cost_to_register() == 0
