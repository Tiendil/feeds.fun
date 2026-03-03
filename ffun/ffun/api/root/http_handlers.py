import xml.etree.ElementTree as ET  # noqa: S405
from typing import Iterable

import fastapi
from fastapi.responses import PlainTextResponse

from ffun.api.root.settings import settings as root_settings
from ffun.application.settings import settings as app_settings
from ffun.core import logging

logger = logging.get_module_logger()

router = fastapi.APIRouter()

api_root = fastapi.APIRouter()


def add_routes_to_app(app: fastapi.FastAPI) -> None:
    app.include_router(api_root)


@api_root.get("/robots.txt")  # type: ignore
async def robots_txt() -> PlainTextResponse:
    lines = [
        "User-agent: *",
        f"Sitemap: https://{app_settings.app_domain}/sitemap.xml",
        "Disallow: /api/",
    ]

    lines.extend(
        [f"Disallow: {path}"
         for path in root_settings.robots_extra_disallowed_paths])

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

    root = ET.Element("sitemapindex", attrib=attributes)

    for url in sorted(sitemap_urls):
        sitemap = ET.SubElement(root, "sitemap")
        location = ET.SubElement(sitemap, "loc")
        location.text = f"https://{app_settings.app_domain}{url}"

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


@api_root.get("/sitemap.xml")  # type: ignore
async def sitemap_xml() -> PlainTextResponse:
    content = build_sitemap_index(root_settings.sitemaps)
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
</urlset>
    """.strip()

    return PlainTextResponse(content, media_type="application/xml; charset=utf-8")
