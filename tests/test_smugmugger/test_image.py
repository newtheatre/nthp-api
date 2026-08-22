"""
Image responses here are hand-built rather than recorded: the fields we care
about are a small, stable part of the SmugMug image and size details objects.
"""

import datetime
from http import HTTPStatus

import httpx
import pytest

from nthp_api.smugmugger import image
from nthp_api.smugmugger.client import SmugMugNotFound

IMAGE_KEY = "ghwm82d"


def make_response(uri: str, payload: dict, status_code=HTTPStatus.OK) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "Code": status_code.value,
            "Message": status_code.phrase,
            "Response": {"Uri": uri, **payload},
        },
    )


def image_payload(**overrides) -> dict:
    return {
        "Image": {
            "ImageKey": IMAGE_KEY,
            "Date": "2013-06-04T12:00:00+00:00",
            "OriginalWidth": 1200,
            "OriginalHeight": 1600,
            **overrides,
        }
    }


SIZE_DETAILS_PAYLOAD = {
    "ImageSizeDetails": {
        "ImageSizeOriginal": {"Width": 1200, "Height": 1600},
        "ImageSizeLarge": {"Width": 600, "Height": 800},
    }
}


class TestGetImageInfo:
    @pytest.mark.asyncio
    async def test_from_image_endpoint(self, make_mock_client):
        requested_urls = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested_urls.append(request.url.path)
            return make_response(request.url.path, image_payload())

        info = await image.get_image_info(make_mock_client(handler), IMAGE_KEY)
        assert info.width == 1200  # noqa: PLR2004
        assert info.height == 1600  # noqa: PLR2004
        assert info.date == datetime.datetime(2013, 6, 4, 12, 0, tzinfo=datetime.UTC)
        assert requested_urls == [f"/api/v2/image/{IMAGE_KEY}"]

    @pytest.mark.asyncio
    async def test_falls_back_to_size_details(self, make_mock_client):
        requested_urls = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested_urls.append(request.url.path)
            if request.url.path.endswith("!sizedetails"):
                return make_response(request.url.path, SIZE_DETAILS_PAYLOAD)
            return make_response(
                request.url.path,
                image_payload(OriginalWidth=None, OriginalHeight=None),
            )

        info = await image.get_image_info(make_mock_client(handler), IMAGE_KEY)
        assert info.width == 1200  # noqa: PLR2004
        assert info.height == 1600  # noqa: PLR2004
        assert requested_urls == [
            f"/api/v2/image/{IMAGE_KEY}",
            f"/api/v2/image/{IMAGE_KEY}!sizedetails",
        ]

    @pytest.mark.asyncio
    async def test_missing_image(self, make_mock_client):
        def handler(request: httpx.Request) -> httpx.Response:
            return make_response(request.url.path, {}, HTTPStatus.NOT_FOUND)

        with pytest.raises(SmugMugNotFound):
            await image.get_image_info(make_mock_client(handler), IMAGE_KEY)
