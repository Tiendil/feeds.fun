import pkg_resources

import ffun

from .settings import settings


def user_agent():
    name = settings.app_name.replace(" ", "")
    version = pkg_resources.get_distribution("ffun").version
    return f"{name}/{version} ({settings.environment} {settings.app_domain})"
