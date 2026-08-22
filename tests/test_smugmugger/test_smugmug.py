import datetime

import pytest

from nthp_api.smugmugger import smugmug
from nthp_api.smugmugger.client import SmugMugNotFound
from nthp_api.smugmugger.schema import SmugMugImageInfo

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
