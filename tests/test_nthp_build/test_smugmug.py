import logging

import pytest
from peewee import SqliteDatabase

from nthp_api.nthp_build import database
from nthp_api.nthp_build.assets import AssetSource, AssetType
from nthp_api.nthp_build.smugmug import (
    async_main,
    fetch_enabled,
    smugmugger_settings,
    update_images,
)
from nthp_api.smugmugger.database import MODELS as SMUGMUGGER_MODELS


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
