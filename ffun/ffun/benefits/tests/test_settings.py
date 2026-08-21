import json

import pydantic
import pytest
from pytest_mock import MockerFixture

from ffun.benefits.entities import (
    BenefitParameterDefinition,
    BenefitParameterId,
    ParameterConstant,
    ParameterReference,
)
from ffun.benefits.settings import Settings
from ffun.benefits.tests.make import make_benefit_package_template
from ffun.domain.entities import BenefitId
from ffun.entitlements.entities import EntitlementKindId


class TestSettings:
    def test_package_template_ids_must_be_unique__accepts_distinct_templates(self) -> None:
        settings = Settings(
            _env_file=None,
            package_templates=(
                make_benefit_package_template(benefit_id=BenefitId("first")),
                make_benefit_package_template(benefit_id=BenefitId("second")),
            ),
        )

        assert [template.id for template in settings.package_templates] == [BenefitId("first"), BenefitId("second")]

    def test_package_template_ids_must_be_unique__rejects_duplicate_id(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="Benefit package template ids must be unique"):
            Settings(
                _env_file=None,
                package_templates=(
                    make_benefit_package_template(benefit_id=BenefitId("duplicate")),
                    make_benefit_package_template(benefit_id=BenefitId("duplicate")),
                ),
            )

    @pytest.mark.parametrize(
        "parameter",
        [
            {"id": "quantity", "maximum": 100},
            {"id": "quantity", "minimum": 1},
        ],
    )
    def test_configuration_parsing__rejects_incomplete_parameter_constraints(
        self,
        parameter: dict[str, object],
        mocker: MockerFixture,
    ) -> None:
        package_template: dict[str, object] = {
            "id": "configured",
            "title": "Configured",
            "description": "Parameterized benefit",
            "parameters": [parameter],
            "entitlements": {"3": {"parameter_id": "quantity"}},
        }
        package_templates: list[dict[str, object]] = [package_template]
        mocker.patch.dict(
            "os.environ",
            {"FFUN_BENEFITS_PACKAGE_TEMPLATES": json.dumps(package_templates)},
        )

        with pytest.raises(pydantic.ValidationError):
            Settings(_env_file=None)

    def test_configuration_parsing__rejects_invalid_constant(self, mocker: MockerFixture) -> None:
        package_template: dict[str, object] = {
            "id": "configured",
            "title": "Configured",
            "description": "Invalid constant",
            "entitlements": {"1": {"value": 0}},
        }
        package_templates: list[dict[str, object]] = [package_template]
        mocker.patch.dict(
            "os.environ",
            {"FFUN_BENEFITS_PACKAGE_TEMPLATES": json.dumps(package_templates)},
        )

        with pytest.raises(pydantic.ValidationError):
            Settings(_env_file=None)

    def test_environment_parsing__loads_nested_package_template_entities(self, mocker: MockerFixture) -> None:
        package_templates = [
            {
                "id": "configured",
                "title": "Test benefit",
                "description": "Test benefit package template",
                "parameters": [{"id": "quantity", "minimum": 1, "maximum": 100}],
                "entitlements": {
                    str(EntitlementKindId.month_tokens.value): {"value": 42},
                    str(EntitlementKindId.lifetime_tokens.value): {"parameter_id": "quantity"},
                },
            }
        ]
        mocker.patch.dict(
            "os.environ",
            {"FFUN_BENEFITS_PACKAGE_TEMPLATES": json.dumps(package_templates)},
        )

        settings = Settings(_env_file=None)

        parameter = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )
        assert settings.package_templates == (
            make_benefit_package_template(
                benefit_id=BenefitId("configured"),
                parameters=(parameter,),
                entitlements={
                    EntitlementKindId.month_tokens: ParameterConstant(value=42),
                    EntitlementKindId.lifetime_tokens: ParameterReference(parameter_id=parameter.id),
                },
            ),
        )
