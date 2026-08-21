import json

import pydantic
import pytest
from pytest_mock import MockerFixture

from ffun.benefits.settings import Settings
from ffun.benefits.tests.make import make_benefit_package
from ffun.domain.entities import BenefitId
from ffun.entitlements.entities import EntitlementKindId


class TestSettings:
    def test_package_ids_must_be_unique__accepts_distinct_packages(self) -> None:
        settings = Settings(
            _env_file=None,
            packages=(
                make_benefit_package(benefit_id=BenefitId("first")),
                make_benefit_package(benefit_id=BenefitId("second")),
            ),
        )

        assert [package.id for package in settings.packages] == [BenefitId("first"), BenefitId("second")]

    def test_package_ids_must_be_unique__rejects_duplicate_id(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="Benefit package ids must be unique"):
            Settings(
                _env_file=None,
                packages=(
                    make_benefit_package(benefit_id=BenefitId("duplicate")),
                    make_benefit_package(benefit_id=BenefitId("duplicate")),
                ),
            )

    def test_environment_parsing__loads_nested_package_entities(self, mocker: MockerFixture) -> None:
        packages = [
            {
                "id": "configured",
                "parameters": {},
                "entitlements": {str(EntitlementKindId.month_tokens.value): 42},
            }
        ]
        mocker.patch.dict("os.environ", {"FFUN_BENEFITS_PACKAGES": json.dumps(packages)})

        settings = Settings(_env_file=None)

        assert settings.packages == (
            make_benefit_package(
                benefit_id=BenefitId("configured"),
                entitlements={EntitlementKindId.month_tokens: 42},
            ),
        )
