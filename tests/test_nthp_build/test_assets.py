import datetime

import pytest

from nthp_api.nthp_build import assets, database, models, schema
from nthp_api.smugmugger import SmugMugImage, SmugMugImageInfo


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            [
                models.Asset(type="frog", image="a"),
                models.Asset(type="poster", image="b"),
            ],
            "b",
        ),
        (
            [
                models.Asset(type="frog", image="a", display_image=True),
                models.Asset(type="poster", image="b"),
            ],
            "a",
        ),
        (
            [
                models.Asset(type="frog", image="a"),
                models.Asset(type="programme", image="b"),
                models.Asset(type="flyer", image="c"),
            ],
            "c",
        ),
        (
            [
                models.Asset(type="programme", image="b"),
            ],
            "b",
        ),
        (
            [
                models.Asset(type="Poster", image="a"),
                models.Asset(type="programme", image="b"),
                models.Asset(type="flyer", image="c"),
            ],
            "a",
        ),
        (
            [
                models.Asset(type="poster", filename="a", title="abc"),
                models.Asset(type="programme", image="b"),
                models.Asset(type="flyer", image="c"),
            ],
            "c",
        ),
    ],
)
def test_pick_show_primary_image(input: list[models.Asset], expected: str):
    assert assets.pick_show_primary_image(input) == expected


THE_TEMPEST_SHOW_ID = "1999-00/the_tempest"


class TestSaveShowAssets:
    def test_title_and_page_are_stored(self, test_db):
        assets.save_show_assets(
            THE_TEMPEST_SHOW_ID,
            [
                schema.Asset(
                    type="other",
                    source="file",
                    mime_type="application/pdf",
                    id="programme.pdf",
                    category="programme",
                    title="Programme",
                    page=3,
                )
            ],
        )
        asset = database.Asset.select().get()
        assert asset.asset_title == "Programme"
        assert asset.asset_page == 3  # noqa: PLR2004

    def test_title_and_page_default_to_null(self, test_db):
        assets.save_show_assets(
            THE_TEMPEST_SHOW_ID,
            [schema.Asset(type="album", source="smugmug", id="abc123")],
        )
        asset = database.Asset.select().get()
        assert asset.asset_title is None
        assert asset.asset_page is None


class TestSmugMugAssetToAsset:
    def test_dimensions_and_date_are_carried_over(self):
        asset = assets.smugmug_asset_to_asset(
            SmugMugImage(
                Uri="/api/v2/album/W38sb3/image/Dg7GGwL-0",
                Date="2013-06-04T12:00:00+00:00",
                FileName="east.jpg",
                Format="JPG",
                ImageKey="Dg7GGwL",
                IsVideo=False,
                OriginalHeight=1600,
                OriginalWidth=1200,
                Processing=False,
                ThumbnailUrl="https://photos.smugmug.com/photos/i-Dg7GGwL/0/Th/x.jpg",
                Title="",
                WebUri="https://photos.newtheatre.org.uk/i-Dg7GGwL",
            )
        )
        assert asset.width == 1200  # noqa: PLR2004
        assert asset.height == 1600  # noqa: PLR2004
        assert asset.date == "2013-06-04T12:00:00+00:00"


class TestAddSmugMugImageInfo:
    @pytest.fixture(autouse=True)
    def _clear_image_info_cache(self):
        assets.get_smugmug_image_info_map.cache_clear()
        yield
        assets.get_smugmug_image_info_map.cache_clear()

    @staticmethod
    def save_poster(image_info: SmugMugImageInfo | None) -> schema.Asset:
        asset = schema.Asset(
            type="image", source="smugmug", id="abc123", category="poster"
        )
        [saved_asset] = assets.save_show_assets("99_00/the_tempest", [asset])
        if image_info is not None:
            saved_asset.asset_smugmug_data = image_info.model_dump_json()
            saved_asset.save()
        return asset

    def test_dimensions_are_added(self, test_db):
        asset = self.save_poster(
            SmugMugImageInfo(
                width=1200,
                height=1600,
                date=datetime.datetime(2013, 6, 4, 12, 0, tzinfo=datetime.UTC),
            )
        )
        enriched_asset = assets.add_smugmug_image_info(asset)
        assert enriched_asset.width == 1200  # noqa: PLR2004
        assert enriched_asset.height == 1600  # noqa: PLR2004
        assert enriched_asset.date == "2013-06-04T12:00:00+00:00"

    def test_unknown_image_keeps_nulls(self, test_db):
        asset = self.save_poster(None)
        enriched_asset = assets.add_smugmug_image_info(asset)
        assert enriched_asset.width is None
        assert enriched_asset.height is None
        assert enriched_asset.date is None

    def test_album_is_left_alone(self, test_db):
        album = schema.Asset(type="album", source="smugmug", id="def456")
        assert assets.add_smugmug_image_info(album) == album
