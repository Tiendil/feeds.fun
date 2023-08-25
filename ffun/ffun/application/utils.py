import pkg_resources

from ffun.application.settings import settings


def user_agent() -> str:
    name = settings.app_name.replace(" ", "")
    version = pkg_resources.get_distribution("ffun").version
    return f"{name}/{version} ({settings.environment} {settings.app_domain})"
