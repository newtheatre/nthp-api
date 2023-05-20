import pytest
from smugmugger import make_client
from smugmugger.client import get_pages


class TestGetPages:
    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_3_pages(self):
        async with make_client() as client:
            images = await get_pages(client, "album/dvVPZh!images", "AlbumImage")
        # Max page size is 100, this should have taken 4 requests,
        # this has been verified by VCR cassette
        assert len(images) == 379
