import pathlib

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
    def test_package_templates__defaults_to_empty(self, mocker: MockerFixture) -> None:
        mocker.patch.dict("os.environ", {}, clear=True)

        settings = Settings(_env_file=None)

        assert settings.package_templates == ()

    def test_package_template_ids_must_be_unique__accepts_distinct_templates(self, tmp_path: pathlib.Path) -> None:
        config_path = tmp_path / "benefit_packages.toml"
        config_path.write_text(
            """
            [[package_templates]]
            id = "first"
            title = "First"
            description = "First package"

            [package_templates.entitlements.day_tokens]
            value = 1

            [[package_templates]]
            id = "second"
            title = "Second"
            description = "Second package"

            [package_templates.entitlements.month_tokens]
            value = 1
            """
        )
        settings = Settings(_env_file=None, package_templates_config=config_path)

        assert [template.id for template in settings.package_templates] == [BenefitId("first"), BenefitId("second")]

    def test_package_template_ids_must_be_unique__rejects_duplicate_id(self, tmp_path: pathlib.Path) -> None:
        config_path = tmp_path / "benefit_packages.toml"
        config_path.write_text(
            """
            [[package_templates]]
            id = "duplicate"
            title = "First"
            description = "First duplicate"

            [package_templates.entitlements.day_tokens]
            value = 1

            [[package_templates]]
            id = "duplicate"
            title = "Second"
            description = "Second duplicate"

            [package_templates.entitlements.month_tokens]
            value = 1
            """
        )

        settings = Settings(_env_file=None, package_templates_config=config_path)

        with pytest.raises(pydantic.ValidationError, match="Benefit package template ids must be unique"):
            settings.package_templates

    @pytest.mark.parametrize(
        "parameter",
        [
            "maximum = 100",
            "minimum = 1",
        ],
    )
    def test_configuration_parsing__rejects_incomplete_parameter_constraints(
        self,
        parameter: str,
        tmp_path: pathlib.Path,
    ) -> None:
        config_path = tmp_path / "benefit_packages.toml"
        config_path.write_text(
            f"""
            [[package_templates]]
            id = "configured"
            title = "Configured"
            description = "Parameterized benefit"

            [[package_templates.parameters]]
            id = "quantity"
            {parameter}

            [package_templates.entitlements.lifetime_tokens]
            parameter_id = "quantity"
            """
        )
        settings = Settings(_env_file=None, package_templates_config=config_path)

        with pytest.raises(pydantic.ValidationError):
            settings.package_templates

    def test_configuration_parsing__rejects_invalid_constant(self, tmp_path: pathlib.Path) -> None:
        config_path = tmp_path / "benefit_packages.toml"
        config_path.write_text(
            """
            [[package_templates]]
            id = "configured"
            title = "Configured"
            description = "Invalid constant"

            [package_templates.entitlements.day_tokens]
            value = 0
            """
        )
        settings = Settings(_env_file=None, package_templates_config=config_path)

        with pytest.raises(pydantic.ValidationError):
            settings.package_templates

    def test_configuration_parsing__rejects_numeric_entitlement_kind(self, tmp_path: pathlib.Path) -> None:
        config_path = tmp_path / "benefit_packages.toml"
        config_path.write_text(
            """
            [[package_templates]]
            id = "configured"
            title = "Configured"
            description = "Numeric entitlement kind"

            [package_templates.entitlements.1]
            value = 1
            """
        )
        settings = Settings(_env_file=None, package_templates_config=config_path)

        with pytest.raises(pydantic.ValidationError, match="Unknown entitlement kind: 1"):
            settings.package_templates

    def test_environment_parsing__loads_nested_package_template_entities(
        self,
        mocker: MockerFixture,
        tmp_path: pathlib.Path,
    ) -> None:
        config_path = tmp_path / "benefit_packages.toml"
        config_path.write_text(
            """
            [[package_templates]]
            id = "configured"
            title = "Test benefit"
            description = "Test benefit package template"

            [[package_templates.parameters]]
            id = "quantity"
            minimum = 1
            maximum = 100

            [package_templates.entitlements.month_tokens]
            value = 42

            [package_templates.entitlements.lifetime_tokens]
            parameter_id = "quantity"
            """
        )
        mocker.patch.dict(
            "os.environ",
            {"FFUN_BENEFITS_PACKAGE_TEMPLATES_CONFIG": str(config_path)},
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
