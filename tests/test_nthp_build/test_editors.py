"""The join between the SmugMug account and the content that references it."""

import datetime
import json

import pytest

from nthp_api.nthp_build import assets, database, editors, models
from nthp_api.nthp_build.assets import AssetSource, AssetTarget, AssetType
from nthp_api.smugmugger import SmugMugImage, SmugMugImageError, SmugMugImageInfo

SHOW_ID = "1999-00/the_tempest"
PERSON_ID = "fred_bloggs"
VENUE_ID = "new_theatre"

HEADSHOTS_ALBUM = "hZh8Jt"
SHOW_ASSETS_ALBUM = "C87GJX"
PROD_SHOTS_ALBUM = "dvVPZh"


def make_image(key: str, file_name: str = "photo.jpg") -> dict:
    return SmugMugImage(
        Uri=f"/api/v2/album/{HEADSHOTS_ALBUM}/image/{key}-0",
        Date=datetime.datetime(2013, 6, 4, 12, 0, tzinfo=datetime.UTC),
        FileName=file_name,
        Format="JPG",
        ImageKey=key,
        IsVideo=False,
        OriginalHeight=1600,
        OriginalWidth=1200,
        Processing=False,
        ThumbnailUrl=f"https://photos.smugmug.com/photos/i-{key}/0/Th/x.jpg",
        Title="",
        WebUri=f"https://photos.newtheatre.org.uk/i-{key}",
    ).model_dump(mode="json", by_alias=True)


def make_album(key: str, name: str, image_keys: list[str] | None = None) -> None:
    database.SmugMugAlbum.create(
        key=key,
        name=name,
        url_name=name.replace(" ", "-"),
        web_uri=f"https://photos.newtheatre.org.uk/{name.replace(' ', '-')}",
        image_count=len(image_keys) if image_keys else 0,
        last_updated="2015-11-06T16:54:32+00:00",
        images=json.dumps([make_image(key) for key in image_keys])
        if image_keys is not None
        else None,
    )


def save_image_asset(
    target_id: str,
    target_type: AssetTarget,
    key: str,
    category: str | None = None,
    info: SmugMugImageInfo | None = None,
) -> database.Asset:
    asset = assets.save_asset(
        target_id=target_id,
        target_type=target_type,
        source=AssetSource.SMUGMUG,
        type=AssetType.IMAGE,
        id=key,
        category=category,
    )
    if info is not None:
        asset.asset_smugmug_data = info.model_dump_json()
        asset.save()
    return asset


@pytest.fixture()
def content(test_db):
    """A show, a person and a venue, each referencing a key of their own."""
    database.Show.create(
        id=SHOW_ID,
        source_path=f"_shows/{SHOW_ID}.md",
        year=1999,
        year_id="1999-00",
        title="The Tempest",
        assets="[]",
        data=models.Show(
            id=SHOW_ID, title="The Tempest", season="In House"
        ).model_dump_json(),
    )
    database.Person.create(
        id=PERSON_ID,
        title="Fred Bloggs",
        headshot="head1",
        data=models.Person(id=PERSON_ID, title="Fred Bloggs").model_dump_json(),
    )
    database.Venue.create(
        id=VENUE_ID,
        name="New Theatre",
        data=models.Venue(id=VENUE_ID, title="New Theatre").model_dump_json(),
    )

    save_image_asset(SHOW_ID, AssetTarget.SHOW, "poster1", category="poster")
    save_image_asset(PERSON_ID, AssetTarget.PERSON, "head1", category="headshot")
    save_image_asset(VENUE_ID, AssetTarget.VENUE, "venue1")
    assets.save_asset(
        target_id=SHOW_ID,
        target_type=AssetTarget.SHOW,
        source=AssetSource.SMUGMUG,
        type=AssetType.ALBUM,
        id=PROD_SHOTS_ALBUM,
    )

    make_album(HEADSHOTS_ALBUM, "Headshots", ["head1", "venue1", "spare1"])
    make_album(SHOW_ASSETS_ALBUM, "Show assets", ["poster1"])
    make_album(PROD_SHOTS_ALBUM, "East 2013")
    make_album("zzzzzz", "Zebra photos", [])
    return test_db


@pytest.fixture()
def uses(content):
    return editors.get_uses_by_key()


class TestUsesByKey:
    def test_an_image_a_show_references_is_used(self, uses):
        assert [use.model_dump() for use in uses["poster1"]] == [
            {
                "target_type": "show",
                "target_id": SHOW_ID,
                "title": "The Tempest",
                "role": "poster",
            }
        ]

    def test_a_venue_image_without_a_category_is_a_photo(self, uses):
        assert uses["venue1"][0].role == "photo"
        assert uses["venue1"][0].title == "New Theatre"

    def test_an_unreferenced_key_has_no_uses(self, uses):
        assert "spare1" not in uses

    def test_trivia_image_references_count_as_uses(self, content):
        database.Trivia.create(
            target_id=SHOW_ID,
            target_type="show",
            target_name="The Tempest",
            target_image_id="trivia1",
            target_year=1999,
            quote="Something happened",
            data="{}",
        )
        uses = editors.get_uses_by_key()
        assert uses["trivia1"][0].role == "trivia"

    def test_trivia_does_not_repeat_a_use_the_content_already_records(self, content):
        database.Trivia.create(
            target_id=SHOW_ID,
            target_type="show",
            target_name="The Tempest",
            target_image_id="poster1",
            target_year=1999,
            quote="Something happened",
            data="{}",
        )
        assert len(editors.get_uses_by_key()["poster1"]) == 1


class TestAlbumInventory:
    def test_lists_every_album_by_name(self, uses):
        inventory = editors.get_album_inventory(uses)
        assert [album.key for album in inventory] == [
            PROD_SHOTS_ALBUM,
            HEADSHOTS_ALBUM,
            SHOW_ASSETS_ALBUM,
            "zzzzzz",
        ]

    def test_an_album_a_show_references_is_used(self, uses):
        inventory = editors.get_album_inventory(uses)
        album = next(album for album in inventory if album.key == PROD_SHOTS_ALBUM)
        assert [use.target_id for use in album.used_by] == [SHOW_ID]
        assert album.used_by[0].role == "album"
        assert album.last_updated == datetime.datetime(
            2015, 11, 6, 16, 54, 32, tzinfo=datetime.UTC
        )

    def test_an_album_nothing_references_is_unused(self, uses):
        inventory = editors.get_album_inventory(uses)
        album = next(album for album in inventory if album.key == HEADSHOTS_ALBUM)
        assert album.used_by == []


class TestImageInventory:
    def get_images(self, uses, album_key: str):
        album = database.SmugMugAlbum.get_by_id(album_key)
        images = editors.get_album_images(album)
        assert images is not None
        inventory = editors.get_image_inventory(album, images, uses)
        return {image.key: image for image in inventory.images}

    def test_an_image_referenced_from_its_own_album_is_used(self, uses):
        images = self.get_images(uses, HEADSHOTS_ALBUM)
        assert [use.target_id for use in images["head1"].used_by] == [PERSON_ID]
        assert images["head1"].used_by[0].role == "headshot"

    def test_an_image_referenced_from_another_album_is_used(self, uses):
        """The venue's photo sits in the headshots album; it still counts as used."""
        images = self.get_images(uses, HEADSHOTS_ALBUM)
        assert [use.target_id for use in images["venue1"].used_by] == [VENUE_ID]

    def test_an_image_nothing_references_is_unused(self, uses):
        images = self.get_images(uses, HEADSHOTS_ALBUM)
        assert images["spare1"].used_by == []

    def test_the_album_is_named_beside_its_images(self, uses):
        album = database.SmugMugAlbum.get_by_id(SHOW_ASSETS_ALBUM)
        images = editors.get_album_images(album)
        assert images is not None
        inventory = editors.get_image_inventory(album, images, uses)
        assert inventory.album.name == "Show assets"
        assert inventory.images[0].file_name == "photo.jpg"

    def test_an_album_whose_images_were_not_fetched_has_none(self, content):
        album = database.SmugMugAlbum.get_by_id(PROD_SHOTS_ALBUM)
        assert editors.get_album_images(album) is None


class TestBrokenRefs:
    def test_reports_the_reason_smugmug_gave(self, content):
        save_image_asset(
            SHOW_ID,
            AssetTarget.SHOW,
            "gone1",
            category="flyer",
            info=SmugMugImageInfo(error=SmugMugImageError.NOT_FOUND),
        )
        save_image_asset(
            SHOW_ID,
            AssetTarget.SHOW,
            "sizeless1",
            info=SmugMugImageInfo(error=SmugMugImageError.NO_DIMENSIONS),
        )
        save_image_asset(
            SHOW_ID,
            AssetTarget.SHOW,
            "flaky1",
            info=SmugMugImageInfo(error=SmugMugImageError.FETCH_FAILED),
        )
        broken = editors.get_broken_refs()
        assert {ref.key: ref.reason for ref in broken} == {
            "gone1": "not_found",
            "sizeless1": "no_dimensions",
            "flaky1": "fetch_failed",
        }
        assert broken[1].role == "flyer"
        assert broken[1].target_id == SHOW_ID
        assert broken[1].title == "The Tempest"

    def test_an_image_with_dimensions_is_not_broken(self, content):
        save_image_asset(
            SHOW_ID,
            AssetTarget.SHOW,
            "fine1",
            info=SmugMugImageInfo(width=1200, height=1600),
        )
        assert [ref.key for ref in editors.get_broken_refs()] == []

    def test_a_key_the_build_never_asked_about_is_not_broken(self, content):
        """Without an API key nothing is fetched; that is unknown, not broken."""
        save_image_asset(SHOW_ID, AssetTarget.SHOW, "unasked1")
        assert [ref.key for ref in editors.get_broken_refs()] == []


class TestEditorsDumpStaysOutOfTheCorpus:
    def test_no_search_documents_are_added(self, content, tmp_path, monkeypatch):
        from nthp_api.nthp_build import dumper
        from nthp_api.nthp_build.parallel import DumperSharedState

        monkeypatch.setattr(dumper, "OUTPUT_DIR", tmp_path)
        state = DumperSharedState(search_documents=[])
        dumper.dump_editors(state=state)
        assert state.search_documents == []
        assert (tmp_path / "editors/smugmug/albums.json").exists()
