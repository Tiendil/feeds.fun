import pytest

from ffun.api.root import http_handlers


class TestRobotsTxt:

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        response = await http_handlers.robots_txt()

        assert response.status_code == 200
        assert response.body.decode() == (
            "User-agent: *\n"
            "Sitemap: feeds.fun.local/sitemap.xml\n"
            "Disallow: /api/\n"
            "Disallow: /show/\n"
            "/blog/en/tags/"
        )


class TestSitemapXml:

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        response = await http_handlers.sitemap_xml()

        assert response.status_code == 200
        assert response.body.decode() == (
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<sitemap><loc>/blog/sitemap.xml</loc></sitemap>"
            "<sitemap><loc>/sitemaps/pages.xml</loc></sitemap>"
            "</sitemapindex>"
        )


class TestSitemapsPagesXml:

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        response = await http_handlers.sitemaps_pages()

        assert response.status_code == 200
        assert response.body.decode() == """
<?xml version="1.0" encoding="UTF-8"?>
<urlset
    xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:xhtml="http://www.w3.org/1999/xhtml" >
  <url>
    <loc>https://feeds.fun.local/</loc>
    <changefreq>daily</changefreq>
  </url>
  <url>
    <loc>https://feeds.fun.local/privacy</loc>
    <changefreq>yearly</changefreq>
  </url>
  <url>
    <loc>https://feeds.fun.local/terms</loc>
    <changefreq>yearly</changefreq>
  </url>
  <url>
    <loc>https://feeds.fun.local/api/docs</loc>
    <changefreq>weekly</changefreq>
  </url>
</urlset>
        """.strip()
