import datetime

import pytest

from nthp_api.smugmugger import smugmug
from nthp_api.smugmugger.client import SmugMugNotFound
from nthp_api.smugmugger.schema import (
    SmugMugAlbum,
    SmugMugAlbumCollection,
    SmugMugImageError,
    SmugMugImageInfo,
)

IMAGE_KEY = "ghwm82d"
IMAGE_INFO = SmugMugImageInfo(
    width=1200,
    height=1600,
    date=datetime.datetime(2013, 6, 4, 12, 0, tzinfo=datetime.UTC),
)


class TestGetImageInfo:
    @pytest.mark.asyncio
    async def test_fetches_once_then_serves_from_cache(self, smug_db, monkeypatch):
        fetch_count = 0

        async def fake_get_image_info(client, image_key):
            nonlocal fetch_count
            fetch_count += 1
            return IMAGE_INFO

        monkeypatch.setattr(
            smugmug.nthp_api.smugmugger.image, "get_image_info", fake_get_image_info
        )

        assert await smugmug.get_image_info(None, IMAGE_KEY) == IMAGE_INFO
        assert await smugmug.get_image_info(None, IMAGE_KEY) == IMAGE_INFO
        assert fetch_count == 1

    @pytest.mark.asyncio
    async def test_caches_missing_image_as_empty(self, smug_db, monkeypatch):
        fetch_count = 0

        async def fake_get_image_info(client, image_key):
            nonlocal fetch_count
            fetch_count += 1
            raise SmugMugNotFound("Not Found")

        monkeypatch.setattr(
            smugmug.nthp_api.smugmugger.image, "get_image_info", fake_get_image_info
        )

        info = await smugmug.get_image_info(None, IMAGE_KEY)
        assert info.has_dimensions is False
        assert info.error is SmugMugImageError.NOT_FOUND
        assert await smugmug.get_image_info(None, IMAGE_KEY) == info
        assert fetch_count == 1

    @pytest.mark.asyncio
    async def test_no_fetch_without_cache_returns_empty(self, smug_db, monkeypatch):
        monkeypatch.setattr(smugmug.settings, "smugmug_fetch", False)
        info = await smugmug.get_image_info(None, IMAGE_KEY)
        assert info.has_dimensions is False
        assert smugmug.get_cached_image_info(IMAGE_KEY) is None

    @pytest.mark.asyncio
    async def test_no_api_key_without_cache_returns_empty(self, smug_db, monkeypatch):
        """No API key should behave like smugmug_fetch=False, not raise."""
        monkeypatch.setattr(smugmug.settings, "smugmug_api_key", None)

        async def fake_get_image_info(client, image_key):
            raise AssertionError("Should not call the API without a key")

        monkeypatch.setattr(
            smugmug.nthp_api.smugmugger.image, "get_image_info", fake_get_image_info
        )

        info = await smugmug.get_image_info(None, IMAGE_KEY)
        assert info.has_dimensions is False
        assert smugmug.get_cached_image_info(IMAGE_KEY) is None

    @pytest.mark.asyncio
    async def test_a_failure_cached_without_a_reason_is_asked_about_again(
        self, smug_db, monkeypatch
    ):
        """Entries cached before reasons were recorded get one on the next build."""
        smugmug.upsert_cached_image_info(IMAGE_KEY, SmugMugImageInfo())

        async def fake_get_image_info(client, image_key):
            raise SmugMugNotFound("Not Found")

        monkeypatch.setattr(
            smugmug.nthp_api.smugmugger.image, "get_image_info", fake_get_image_info
        )

        info = await smugmug.get_image_info(None, IMAGE_KEY)
        assert info.error is SmugMugImageError.NOT_FOUND

    def test_image_cache_is_namespaced_from_albums(self, smug_db):
        smugmug.upsert_cached_image_info(IMAGE_KEY, IMAGE_INFO)
        assert smugmug.get_cached_album_images(IMAGE_KEY) is None
        assert smugmug.get_cached_image_info(IMAGE_KEY) == IMAGE_INFO


class TestGetAlbumImages:
    @pytest.mark.asyncio
    async def test_no_api_key_without_cache_returns_empty(self, smug_db, monkeypatch):
        """No API key should behave like smugmug_fetch=False, not raise."""
        monkeypatch.setattr(smugmug.settings, "smugmug_api_key", None)

        async def fake_get_album(client, album_id):
            raise AssertionError("Should not call the API without a key")

        monkeypatch.setattr(
            smugmug.nthp_api.smugmugger.album, "get_album", fake_get_album
        )

        images = await smugmug.get_album_images(None, "dvVPZh")
        assert len(images) == 0
        assert smugmug.get_cached_album_images("dvVPZh") is None


ALBUM_KEY = "W38sb3"
ALBUMS = SmugMugAlbumCollection(
    [
        SmugMugAlbum(
            Uri=f"/api/v2/album/{ALBUM_KEY}",
            AlbumKey=ALBUM_KEY,
            ImagesLastUpdated=datetime.datetime(
                2015, 11, 6, 16, 55, tzinfo=datetime.UTC
            ),
            LastUpdated=datetime.datetime(2015, 11, 6, 16, 54, tzinfo=datetime.UTC),
            Name="East 2013",
            NiceName="East-2013",
            UrlName="East-2013",
            WebUri="https://photos.newtheatre.org.uk/2012-13/East-2013",
            ImageCount=379,
        )
    ]
)
NICKNAME = "newtheatre"


class TestGetUserAlbums:
    @pytest.mark.asyncio
    async def test_fetches_once_then_serves_from_cache(self, smug_db, monkeypatch):
        fetch_count = 0

        async def fake_get_user_albums(client, nickname):
            nonlocal fetch_count
            fetch_count += 1
            return ALBUMS

        monkeypatch.setattr(
            smugmug.nthp_api.smugmugger.album, "get_user_albums", fake_get_user_albums
        )

        assert await smugmug.get_user_albums(None, NICKNAME) == ALBUMS
        assert await smugmug.get_user_albums(None, NICKNAME) == ALBUMS
        assert fetch_count == 1

    @pytest.mark.asyncio
    async def test_no_fetch_without_cache_returns_empty(self, smug_db, monkeypatch):
        monkeypatch.setattr(smugmug.settings, "smugmug_fetch", False)
        assert await smugmug.get_user_albums(None, NICKNAME) == SmugMugAlbumCollection()

    def test_album_sweep_cache_is_namespaced_from_albums(self, smug_db):
        smugmug.upsert_cached_user_albums(NICKNAME, ALBUMS)
        assert smugmug.get_cached_album_images(NICKNAME) is None
        assert smugmug.get_cached_user_albums(NICKNAME) == ALBUMS
