
from ffun.core import utils
from ffun.application.settings import settings


def user_agent() -> str:
    name = settings.app_name.replace(" ", "")
    package_version = utils.version()
    return f"{name}/{package_version} ({settings.environment} {settings.app_domain})"
