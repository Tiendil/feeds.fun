import httpx
import pytest
from pytest_mock import MockerFixture
from respx.router import MockRouter

from ffun.domain import http


class TestClient:

    @pytest.mark.parametrize(
        "bytes_content, expected_headers",
        [
            (b"test-response", {}),
            (
                b"\x1f\x8b\x08\x00v\x18Sf\x02\xff+I-.\xd1-J-.\xc8\xcf+N\x05\x00\xfe\xebMu\r\x00\x00\x00",
                {"Content-Encoding": "gzip"},
            ),
            (b"x\x9c+I-.\xd1-J-.\xc8\xcf+N\x05\x00%A\x05]", {"Content-Encoding": "deflate"}),
            (b"(\xb5/\xfd \ri\x00\x00test-response", {"Content-Encoding": "zstd"}),
            (b"\x1b\x0c\x00\xf8\xa5[\xca\xe6\xe8\x84+\xa1\xc66", {"Content-Encoding": "br"}),
        ],
        ids=["plain", "gzip", "deflate", "zstd", "br"],
    )
    @pytest.mark.asyncio
    async def test_compressing_support(
        self, respx_mock: MockRouter, bytes_content: bytes, expected_headers: dict[str, str]
    ) -> None:
        expected_content = "test-response"

        mocked_response = httpx.Response(200, headers=expected_headers, content=bytes_content)

        respx_mock.get("/test").mock(return_value=mocked_response)

        async with http.client() as client:
            response = await client.get("http://example.com/test")

        assert response.text == expected_content

    @pytest.mark.asyncio
    async def test_accept_encoding_header(self, respx_mock: MockRouter) -> None:
        respx_mock.get("/test").mock()

        async with http.client() as client:
            await client.get("http://example.com/test")

        assert (
            respx_mock.calls[0].request.headers["Accept-Encoding"] == "br;q=1.0, zstd;q=0.9, gzip;q=0.8, deflate;q=0.7"
        )

    @pytest.mark.asyncio
    async def test_user_agent_header(self, respx_mock: MockRouter, mocker: MockerFixture) -> None:
        test_user_agent = "test-user-agent/1.0"

        mocker.patch("ffun.domain.http._user_agent", test_user_agent)

        respx_mock.get("/test").mock()

        async with http.client() as client:
            await client.get("http://example.com/test")

        assert respx_mock.calls[0].request.headers["User-Agent"] == test_user_agent
