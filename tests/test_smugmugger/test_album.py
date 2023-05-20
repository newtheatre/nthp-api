import datetime

import pytest
from smugmugger import album, make_client
from smugmugger.client import SmugMugNotFound


class TestGetAlbum:
    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_east(self):
        async with make_client() as client:
            east = await album.get_album(client, "dvVPZh")
        assert east.Name == "East 2013"
        assert east.ImagesLastUpdated == datetime.datetime(
            2015, 11, 6, 16, 55, 22, tzinfo=datetime.timezone.utc
        )


class TestGetAlbumImages:
    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_east(self):
        async with make_client() as client:
            images = await album.get_album_images(client, "dvVPZh")
        assert len(images) == 379
        first_image = images[0]
        assert first_image.ImageKey == "gKfJkMG"
        assert first_image.IsVideo is False
        assert first_image.FileName == "467755_10151632779041460_637244986_o.jpg"
        assert (
            first_image.ThumbnailUrl
            == "https://photos.smugmug.com/photos/i-gKfJkMG/0/Th/i-gKfJkMG-Th.jpg"
        )
        assert (
            first_image.WebUri
            == "https://photos.newtheatre.org.uk/2012-13/East-2013/i-gKfJkMG"
        )

    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_single_image_album(self):
        async with make_client() as client:
            images = await album.get_album_images(client, "W38sb3")
        assert len(images) == 1
        image = images[0]
        assert image.ImageKey == "Dg7GGwL"

    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_not_found(self):
        with pytest.raises(SmugMugNotFound):
            async with make_client() as client:
                await album.get_album_images(client, "abc123")
