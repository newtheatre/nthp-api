import datetime
import logging

import pytest
from peewee import SqliteDatabase

from nthp_api.nthp_build import database
from nthp_api.nthp_build.assets import AssetSource, AssetType
from nthp_api.nthp_build.config import settings as build_settings
from nthp_api.nthp_build.smugmug import (
    async_main,
    fetch_enabled,
    smugmugger_settings,
    update_album_inventory,
    update_images,
)
from nthp_api.smugmugger.database import MODELS as SMUGMUGGER_MODELS
from nthp_api.smugmugger.schema import (
    SmugMugAlbum,
    SmugMugAlbumCollection,
    SmugMugImageCollection,
)


@pytest.fixture()
def smug_db():
    smug_db = SqliteDatabase(":memory:")
    with smug_db.bind_ctx(SMUGMUGGER_MODELS):
        smug_db.create_tables(SMUGMUGGER_MODELS)
        try:
            yield smug_db
        finally:
            smug_db.drop_tables(SMUGMUGGER_MODELS)
            smug_db.close()


def make_image_asset(image_key: str) -> database.Asset:
    return database.Asset.create(
        target_id="some-show",
        target_type="show",
        asset_source=AssetSource.SMUGMUG,
        asset_type=AssetType.IMAGE,
        asset_id=image_key,
    )


class TestFetchEnabled:
    def test_true_when_fetch_on_and_key_present(self, monkeypatch):
        monkeypatch.setattr(smugmugger_settings, "smugmug_fetch", True)
        monkeypatch.setattr(smugmugger_settings, "smugmug_api_key", "test-key")
        assert fetch_enabled() is True

    def test_false_without_api_key(self, monkeypatch):
        monkeypatch.setattr(smugmugger_settings, "smugmug_fetch", True)
        monkeypatch.setattr(smugmugger_settings, "smugmug_api_key", None)
        assert fetch_enabled() is False

    def test_false_when_fetch_disabled(self, monkeypatch):
        monkeypatch.setattr(smugmugger_settings, "smugmug_fetch", False)
        monkeypatch.setattr(smugmugger_settings, "smugmug_api_key", "test-key")
        assert fetch_enabled() is False


class TestUpdateImagesWithoutApiKey:
    @pytest.mark.asyncio
    async def test_no_error_logs_and_no_dimensions_warning(
        self, test_db, smug_db, monkeypatch, caplog
    ):
        monkeypatch.setattr(smugmugger_settings, "smugmug_fetch", True)
        monkeypatch.setattr(smugmugger_settings, "smugmug_api_key", None)
        make_image_asset("ghwm82d")

        with caplog.at_level(logging.DEBUG):
            updated_count = await update_images(None)

        assert updated_count == 0
        assert not any(
            record.levelno >= logging.WARNING for record in caplog.records
        ), [r.message for r in caplog.records]


class TestAsyncMainWarnsOnceWithoutApiKey:
    @pytest.mark.asyncio
    async def test_single_warning_for_missing_key(
        self, test_db, smug_db, monkeypatch, caplog
    ):
        monkeypatch.setattr(smugmugger_settings, "smugmug_fetch", True)
        monkeypatch.setattr(smugmugger_settings, "smugmug_api_key", None)
        make_image_asset("ghwm82d")
        make_image_asset("anotherkey")

        with caplog.at_level(logging.WARNING):
            await async_main()

        warnings = [
            record.message
            for record in caplog.records
            if record.levelno == logging.WARNING
        ]
        assert len(warnings) == 1
        assert "No SmugMug API key configured" in warnings[0]

    @pytest.mark.asyncio
    async def test_no_warning_when_fetch_explicitly_disabled(
        self, test_db, smug_db, monkeypatch, caplog
    ):
        monkeypatch.setattr(smugmugger_settings, "smugmug_fetch", False)
        monkeypatch.setattr(smugmugger_settings, "smugmug_api_key", None)

        with caplog.at_level(logging.WARNING):
            await async_main()

        assert caplog.records == []


class TestUpdateImagesGenuineFailure:
    @pytest.mark.asyncio
    async def test_per_image_failure_still_logged_when_key_present(
        self, test_db, smug_db, monkeypatch, caplog
    ):
        monkeypatch.setattr(smugmugger_settings, "smugmug_fetch", True)
        monkeypatch.setattr(smugmugger_settings, "smugmug_api_key", "test-key")
        make_image_asset("ghwm82d")

        async def failing_get_image_info(client, image_key):
            raise ValueError("boom")

        import nthp_api.nthp_build.smugmug as smugmug_module

        monkeypatch.setattr(
            smugmug_module.smugmugger, "get_image_info", failing_get_image_info
        )

        with caplog.at_level(logging.DEBUG):
            updated_count = await update_images(None)

        assert updated_count == 0
        assert any(
            "Failed to fetch image info for ghwm82d" in record.message
            for record in caplog.records
        )


def make_album(key: str, name: str, image_count: int = 1) -> SmugMugAlbum:
    return SmugMugAlbum(
        Uri=f"/api/v2/album/{key}",
        AlbumKey=key,
        ImagesLastUpdated=datetime.datetime(2015, 11, 6, 16, 55, tzinfo=datetime.UTC),
        LastUpdated=datetime.datetime(2015, 11, 6, 16, 54, tzinfo=datetime.UTC),
        Name=name,
        NiceName=name.replace(" ", "-"),
        UrlName=name.replace(" ", "-"),
        WebUri=f"https://photos.newtheatre.org.uk/{name.replace(' ', '-')}",
        ImageCount=image_count,
    )


UTILITY_ALBUM_KEY = "hZh8Jt"
REFERENCED_ALBUM_KEY = "dvVPZh"
UNREFERENCED_ALBUM_KEY = "W38sb3"
ACCOUNT_ALBUM_COUNT = 3


class TestUpdateAlbumInventory:
    @pytest.fixture()
    def swept(self, test_db, smug_db, monkeypatch):
        """The account holds three albums; the content references one of them."""
        monkeypatch.setattr(
            build_settings, "smugmug_utility_album_keys", [UTILITY_ALBUM_KEY]
        )
        database.Asset.create(
            target_id="some-show",
            target_type="show",
            asset_source=AssetSource.SMUGMUG,
            asset_type=AssetType.ALBUM,
            asset_id=REFERENCED_ALBUM_KEY,
        )
        albums_fetched = []

        async def fake_get_user_albums(client, nickname):
            return SmugMugAlbumCollection(
                [
                    make_album(UTILITY_ALBUM_KEY, "Headshots"),
                    make_album(REFERENCED_ALBUM_KEY, "East 2013"),
                    make_album(UNREFERENCED_ALBUM_KEY, "Zebra photos"),
                ]
            )

        async def fake_get_album_images(client, album_key):
            albums_fetched.append(album_key)
            return SmugMugImageCollection()

        import nthp_api.nthp_build.smugmug as smugmug_module

        monkeypatch.setattr(
            smugmug_module.smugmugger, "get_user_albums", fake_get_user_albums
        )
        monkeypatch.setattr(
            smugmug_module.smugmugger, "get_album_images", fake_get_album_images
        )
        return albums_fetched

    @pytest.mark.asyncio
    async def test_records_every_album_in_the_account(self, swept):
        assert await update_album_inventory(None) == ACCOUNT_ALBUM_COUNT
        assert {album.key for album in database.SmugMugAlbum.select()} == {
            UTILITY_ALBUM_KEY,
            REFERENCED_ALBUM_KEY,
            UNREFERENCED_ALBUM_KEY,
        }

    @pytest.mark.asyncio
    async def test_images_are_fetched_only_where_keys_are_picked_from(self, swept):
        await update_album_inventory(None)
        assert sorted(swept) == sorted([UTILITY_ALBUM_KEY, REFERENCED_ALBUM_KEY])
        unreferenced = database.SmugMugAlbum.get_by_id(UNREFERENCED_ALBUM_KEY)
        assert unreferenced.images is None
        assert unreferenced.name == "Zebra photos"
        assert database.SmugMugAlbum.get_by_id(UTILITY_ALBUM_KEY).images == "[]"

    @pytest.mark.asyncio
    async def test_an_album_the_sweep_does_not_list_is_asked_about_by_key(
        self, swept, monkeypatch
    ):
        """The utility albums are reachable by key but absent from the sweep."""
        unlisted_key = "j3PdMh"
        monkeypatch.setattr(
            build_settings,
            "smugmug_utility_album_keys",
            [UTILITY_ALBUM_KEY, unlisted_key],
        )
        asked_about = []

        async def fake_get_album(client, album_key):
            asked_about.append(album_key)
            return make_album(album_key, "Show assets")

        import nthp_api.nthp_build.smugmug as smugmug_module

        monkeypatch.setattr(smugmug_module.smugmugger, "get_album", fake_get_album)

        await update_album_inventory(None)
        assert asked_about == [unlisted_key]
        assert database.SmugMugAlbum.get_by_id(unlisted_key).name == "Show assets"
        assert unlisted_key in swept

    @pytest.mark.asyncio
    async def test_a_second_run_replaces_rather_than_duplicates(self, swept):
        await update_album_inventory(None)
        await update_album_inventory(None)
        assert database.SmugMugAlbum.select().count() == ACCOUNT_ALBUM_COUNT
