import enum

import pydantic
import pydantic_settings

from ffun.domain.entities import AuthServiceId
from ffun.core.settings import BaseSettings


# default values for service ids
# used to simplify unit tests
primary_oidc_service_id = AuthServiceId(1)
single_user_service_id = AuthServiceId(2)


class AuthMode(str, enum.Enum):
    single_user = "single_user"
    oidc = "oidc"


class SingleUser(pydantic.BaseModel):
    external_id: str = "user-for-development"


class OIDC(pydantic.BaseModel):
    header_user_id: str = "X-FFun-User-Id"
    header_identity_provider_id: str = "X-FFun-Identity-Provider-Id"


class Settings(BaseSettings):
    mode: AuthMode = AuthMode.single_user
    single_user: SingleUser = SingleUser()
    oidc: OIDC = OIDC()

    auth_service_map: dict[str, AuthServiceId] = pydantic.Field(
        default_factory=lambda: {
            "primary_oidc": primary_oidc_service_id,
            "single_user": single_user_service_id,
        }
    )

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="FFUN_AUTH_")


settings = Settings()
