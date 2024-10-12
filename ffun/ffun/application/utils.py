from importlib.metadata import version

from ffun.application.settings import settings


def user_agent() -> str:
    name = settings.app_name.replace(" ", "")
    package_version = version("ffun")
    return f"{name}/{package_version} ({settings.environment} {settings.app_domain})"
