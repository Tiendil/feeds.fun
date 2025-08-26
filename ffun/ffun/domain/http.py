from typing import Any

import httpx

from ffun.core import logging

logger = logging.get_module_logger()


_user_agent: str = "unknown"

_accept_enconding_header = "br;q=1.0, zstd;q=0.9, gzip;q=0.8, deflate;q=0.7"


def set_user_agent(user_agent: str) -> None:
    global _user_agent
    logger.info("set_user_agent", user_agent=user_agent)
    _user_agent = user_agent


def get_user_agent() -> str:
    return _user_agent


def client(proxy: str | None = None, headers: Any = None, timeout: float | None = None) -> httpx.AsyncClient:
    attributes: dict[str, Any] = {"http2": True}

    if proxy is not None:
        attributes["proxy"] = proxy

    attributes["headers"] = {
        "User-Agent": get_user_agent(),
        "Accept-Encoding": _accept_enconding_header,
        **(headers or {}),
    }

    if timeout is not None:
        attributes["timeout"] = timeout

    return httpx.AsyncClient(**attributes)
