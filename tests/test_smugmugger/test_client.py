import pytest

from nthp_api.smugmugger.client import get_pages, make_client


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
