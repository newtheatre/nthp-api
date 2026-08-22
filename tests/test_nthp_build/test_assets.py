import pytest

from nthp_api.nthp_build import assets, database, models, schema


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
