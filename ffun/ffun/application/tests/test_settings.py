import pytest

from ffun.application.settings import Settings


class TestSettings:
    def test_origin_must_be_redefined_in_prod(self) -> None:
        with pytest.raises(ValueError):
            Settings(environment="prod")

        settings = Settings(environment="prod", origins=("http://localhost:3000", "http://localhost:3001"))

        assert settings.origins == ("http://localhost:3000", "http://localhost:3001")
