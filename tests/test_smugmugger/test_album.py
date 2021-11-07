import datetime

import pytest

from smugmugger import album, client


class TestGetAlbum:
    @pytest.mark.vcr
    def test_east(self):
        east = album.get_album("dvVPZh")
        assert east.Name == "East 2013"
        assert east.ImagesLastUpdated == datetime.datetime(
            2015, 11, 6, 16, 55, 22, tzinfo=datetime.timezone.utc
        )


class TestGetAlbumImages:
    @pytest.mark.vcr
    def test_east(self):
        images = album.get_album_images("dvVPZh")
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

    @pytest.mark.vcr
    def test_single_image_album(self):
        images = album.get_album_images("W38sb3")
        assert len(images) == 1
        image = images[0]
        assert image.ImageKey == "Dg7GGwL"

    @pytest.mark.vcr
    def test_not_found(self):
        with pytest.raises(client.SmugMugNotFound):
            album.get_album_images("abc123")
