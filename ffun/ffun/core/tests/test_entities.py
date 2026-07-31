import pydantic
import pytest

from ffun.core.entities import NonEmptyString


class TestNonEmptyString:
    def test_init__normalizes_value(self) -> None:
        assert NonEmptyString(" value ") == NonEmptyString("value")

    @pytest.mark.parametrize("value", ["", " "])
    def test_init__rejects_empty_value(self, value: str) -> None:
        with pytest.raises(ValueError, match="NonEmptyString must not be empty"):
            NonEmptyString(value)

    def test_pydantic_schema__normalizes_value(self) -> None:
        adapter = pydantic.TypeAdapter(NonEmptyString)

        value = adapter.validate_python(" value ")

        assert value == NonEmptyString("value")
        assert isinstance(value, NonEmptyString)

    @pytest.mark.parametrize("value", ["", " "])
    def test_pydantic_schema__rejects_empty_value(self, value: str) -> None:
        adapter = pydantic.TypeAdapter(NonEmptyString)

        with pytest.raises(pydantic.ValidationError, match="NonEmptyString must not be empty"):
            adapter.validate_python(value)
