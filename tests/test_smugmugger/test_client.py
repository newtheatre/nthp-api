import pytest

from smugmugger import client


class TestGetPages:
    @pytest.mark.vcr
    def test_3_pages(self):
        url = "album/dvVPZh!images"
        images = client.get_pages(url, "AlbumImage")
        # Max page size is 100, this should have taken 4 requests
        assert len(images) == 379
