
import pytest

from ffun.llms_framework import errors
from ffun.llms_framework.domain import split_text, split_text_according_to_tokens
from ffun.llms_framework.provider_interface import ProviderTest
from ffun.llms_framework.entities import LLMConfiguration


class TestSplitText:

    @pytest.mark.parametrize("parts_number", [-100, -1, 0])
    def test_wrong_parts_number(self, parts_number: int) -> None:
        with pytest.raises(errors.TextPartsMustBePositive):
            split_text("some-text", parts=parts_number, intersection=0)

    @pytest.mark.parametrize("intersection", [-100, -1])
    def test_intersection_size(self, intersection: int) -> None:
        with pytest.raises(errors.TextIntersectionMustBePositiveOrZero):
            split_text("some-text", parts=1, intersection=intersection)

    def test_text_is_empty(self) -> None:
        with pytest.raises(errors.TextIsEmpty):
            split_text("", parts=1, intersection=0)

    def test_text_is_too_short(self) -> None:
        with pytest.raises(errors.TextIsTooShort):
            split_text("short", parts=len("short") + 1, intersection=0)

        with pytest.raises(errors.TextIsTooShort):
            split_text("some-text", parts=4, intersection=0)

    @pytest.mark.parametrize("text",
                             ['small-text', 'long-long-text ' * 10**6],
                             ids=['small', 'big'])
    def test_single_part(self, text: str) -> None:
        for intersection in [0, 1, 100, 1000, 10000]:
            assert split_text(text, parts=1, intersection=intersection) == [text]

    @pytest.mark.parametrize("text, parts, intersection, expected",
                             [('some-text', 1, 0, ['some-text']),
                              ('some-text', 2, 0, ['some-', 'text']),
                              ('some-text', 3, 0, ['som', 'e-t', 'ext']),

                              ('some-text', 1, 1, ['some-text']),
                              ('some-text', 2, 1, ['some-t', '-text']),
                              ('some-text', 3, 1, ['some', 'me-te', 'text']),

                              ('some-text', 1, 2, ['some-text']),
                              ('some-text', 2, 2, ['some-te', 'e-text']),
                              ('some-text', 3, 2, ['some-', 'ome-tex', '-text']),

                              ('some-text', 1, 3, ['some-text']),
                              ('some-text', 2, 3, ['some-tex', 'me-text']),
                              ('some-text', 3, 3, ['some-t', 'some-text', 'e-text']),
                              ])
    def test_split(self, text: str, parts: int, intersection: int, expected: list[str]) -> None:
        assert split_text(text, parts=parts, intersection=intersection) == expected


class TestSplitTextAccordingToTokens:

    @pytest.fixture
    def llm_config(self) -> LLMConfiguration:
        return LLMConfiguration(model='test-model-1',
                                system="system prompt",
                                max_return_tokens=143,
                                text_parts_intersection=100,
                                temperature=0,
                                top_p=0,
                                presence_penalty=0,
                                frequency_penalty=0)

    def test_single_part(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        text = "some text"

        parts = split_text_according_to_tokens(llm=fake_llm_provider, llm_config=llm_config, text=text)

        assert parts == [text]

    def test_multiple_parts(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        # We test that algorithm will pass a few iterations before finding the right split
        # => for this test, text must be splittable to 3 parts

        model = fake_llm_provider.get_model(llm_config)

        size = int(model.max_context_size * 2.5)

        text = "a" * size

        parts = split_text_according_to_tokens(llm=fake_llm_provider, llm_config=llm_config, text=text)

        assert len(parts) == 3

        assert size < sum(len(part) for part in parts) < size + 2 * 2 * llm_config.text_parts_intersection + 1

        assert abs(len(parts[0]) - len(parts[1])) <= llm_config.text_parts_intersection + 1
        assert abs(len(parts[1]) - len(parts[2])) <= llm_config.text_parts_intersection + 1
        assert abs(len(parts[0]) - len(parts[2])) <= 1

    def test_too_many_tokens_for_entry(self, fake_llm_provider: ProviderTest, llm_config: LLMConfiguration) -> None:
        model = fake_llm_provider.get_model(llm_config)

        text = "a" * (model.max_tokens_per_entry + 1)

        with pytest.raises(errors.TooManyTokensForEntry):
            split_text_according_to_tokens(llm=fake_llm_provider, llm_config=llm_config, text=text)
