from http import HTTPStatus

import httpx
import pytest

from nthp_api.smugmugger.client import (
    SmugMugApiError,
    SmugMugNotFound,
    get,
    get_pages,
    make_client,
)
from nthp_api.smugmugger.config import settings


class TestGetPages:
    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_3_pages(self):
        async with make_client() as client:
            images = await get_pages(client, "album/dvVPZh!images", "AlbumImage")
        # Max page size is 100, this should have taken 4 requests,
        # this has been verified by VCR cassette
        expected_number_of_images = 379
        assert len(images) == expected_number_of_images


def make_status_response(status_code: HTTPStatus, headers=None) -> httpx.Response:
    return httpx.Response(
        status_code,
        headers=headers,
        json={
            "Code": status_code.value,
            "Message": status_code.phrase,
            "Response": {"Uri": "/api/v2/image/ghwm82d"},
        },
    )


class TestRedirects:
    @pytest.mark.asyncio
    async def test_bare_image_key_redirect_is_followed(
        self, make_mock_client, monkeypatch
    ):
        monkeypatch.setattr(settings, "smugmug_api_key", "test-key")
        requested_paths = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested_paths.append(request.url.path)
            if request.url.path.endswith("-0"):
                return httpx.Response(
                    HTTPStatus.OK,
                    json={
                        "Code": 200,
                        "Message": "Ok",
                        "Response": {"Uri": request.url.path},
                    },
                )
            return httpx.Response(
                HTTPStatus.MOVED_PERMANENTLY,
                headers={"Location": f"{request.url.path}-0"},
            )

        await get(make_mock_client(handler), "image/ghwm82d")
        assert requested_paths == ["/api/v2/image/ghwm82d", "/api/v2/image/ghwm82d-0"]


class TestRetries:
    @pytest.fixture(autouse=True)
    def _no_backoff_delay(self, monkeypatch):
        monkeypatch.setattr(settings, "smugmug_retry_backoff_seconds", 0)

    @pytest.mark.asyncio
    async def test_retries_rate_limit_then_succeeds(self, make_mock_client):
        statuses = [HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.OK]

        def handler(request: httpx.Request) -> httpx.Response:
            return make_status_response(statuses.pop(0), headers={"Retry-After": "0"})

        response = await get(make_mock_client(handler), "image/ghwm82d")
        assert response["Code"] == HTTPStatus.OK
        assert statuses == []

    @pytest.mark.asyncio
    async def test_gives_up_on_repeated_server_errors(self, make_mock_client):
        attempt_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return make_status_response(HTTPStatus.SERVICE_UNAVAILABLE)

        with pytest.raises(SmugMugApiError):
            await get(make_mock_client(handler), "image/ghwm82d")
        assert attempt_count == settings.smugmug_retry_attempts

    @pytest.mark.asyncio
    async def test_does_not_retry_not_found(self, make_mock_client):
        attempt_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return make_status_response(HTTPStatus.NOT_FOUND)

        with pytest.raises(SmugMugNotFound):
            await get(make_mock_client(handler), "image/ghwm82d")
        assert attempt_count == 1
