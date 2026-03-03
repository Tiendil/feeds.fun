from importlib import metadata
from typing import Iterable

import fastapi
import xml.etree.ElementTree as ET
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

from ffun.api.spa import entities
from ffun.api.spa.settings import settings
from ffun.auth import domain as a_domain
from ffun.auth.dependencies import User
from ffun.auth.settings import settings as auth_settings
from ffun.core import logging, utils
from ffun.core.api import Message, MessageType
from ffun.core.errors import APIError
from ffun.data_protection import domain as dp_domain
from ffun.domain.entities import TagId, TagUid, UserId
from ffun.domain.urls import url_to_uid
from ffun.feeds import domain as f_domain
from ffun.feeds_collections.collections import collections
from ffun.feeds_discoverer import domain as fd_domain
from ffun.feeds_discoverer import entities as fd_entities
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.markers import domain as m_domain
from ffun.meta import domain as meta_domain
from ffun.ontology import domain as o_domain
from ffun.parsers import domain as p_domain
from ffun.parsers import entities as p_entities
from ffun.resources import domain as r_domain
from ffun.scores import domain as s_domain
from ffun.scores import entities as s_entities
from ffun.user_settings import domain as us_domain
from ffun.application.settings import settings as app_settings
from ffun.api.root.settings import settings as root_settings

logger = logging.get_module_logger()

router = fastapi.APIRouter()

api_root = fastapi.APIRouter(prefix="/")


def add_routes_to_app(app: fastapi.FastAPI) -> None:
    app.include_router(api_root)


@api_root.get("/robots.txt")  # type: ignore
async def robots_txt() -> PlainTextResponse:
    lines = [
        "User-agent: *",
        f"Sitemap: {app_settings.app_domain}/sitemap.xml",
        "Disallow: /api/",
        "Disallow: /show/",
    ]

    lines.extend(root_settings.robots_extra_disallowed_paths)

    content = "\n".join(lines)

    return PlainTextResponse(content)

# Sitemap: https://feeds.fun/blog/sitemap.xml
# Disallow: /blog/en/tags/


def build_sitemap_index(
    sitemap_urls: Iterable[str],
) -> str:

    attributes = {
        "xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9",
    }

    root = ET.Element("sitemapindex", **attributes)

    for url in sorted(sitemap_urls):
        sitemap = ET.SubElement(root, "sitemap")
        location = ET.SubElement(sitemap, "loc")
        location.text = url

    return ET.tostring(root, encoding="unicode")


@api_root.get("/sitemap.xml")  # type: ignore
async def sitemap_xml() -> PlainTextResponse:
    content = build_sitemap_index(root_settings.sitemap_urls)
    return PlainTextResponse(content, media_type="application/xml; charset=utf-8")


@api_root.get("/sitemaps/pages.xml")  # type: ignore
async def sitemaps_pages() -> PlainTextResponse:
    content = f"""
<?xml version="1.0" encoding="UTF-8"?>
<urlset
    xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:xhtml="http://www.w3.org/1999/xhtml" >
  <url>
    <loc>https://{app_settings.app_domain}/</loc>
    <changefreq>daily</changefreq>
  </url>
  <url>
    <loc>https://{app_settings.app_domain}/privacy</loc>
    <changefreq>yearly</changefreq>
  </url>
  <url>
    <loc>https://{app_settings.app_domain}/terms</loc>
    <changefreq>yearly</changefreq>
  </url>
  <url>
    <loc>https://{app_settings.app_domain}/api/docs</loc>
    <changefreq>weekly</changefreq>
  </url>
</urlset>
    """.strip()

    return PlainTextResponse(content, media_type="application/xml; charset=utf-8")
