from ffun.application.settings import settings
from ffun.core import utils


def user_agent() -> str:
    name = settings.app_name.replace(" ", "")
    package_version = utils.version()
    return f"{name}/{package_version} ({settings.environment} {settings.app_domain})"
