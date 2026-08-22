import json
import logging
from pathlib import Path

import pytest

from nthp_api.nthp_build import assets, database, dumper, models, spec, venues
from nthp_api.nthp_build.parallel import DumperSharedState
from nthp_api.smugmugger import SmugMugImageInfo

NEW_THEATRE_BUILT = 1965
C_SOCO_SHOW_IDS = ["1999-00/fringe_show", "1999-00/other_fringe_show"]


@pytest.mark.parametrize(
    "input,expected",
    [
        ("New Theatre", "new-theatre"),
        ("Nëd Thöoter ", "ned-thooter"),
        ("Lee Rosy's Tea Rooms", "lee-rosys-tea-rooms"),
    ],
)
def test_get_venue_id(input: str, expected: str):
    assert venues.get_venue_id(input) == expected


def make_show(
    show_id: str,
    title: str,
    venue: str | None,
    venue_sort: str | None = None,
    date_start: str | None = None,
) -> database.Show:
    return database.Show.create(
        id=show_id,
        source_path=f"_shows/{show_id}.md",
        year=1999,
        year_id="1999-00",
        title=title,
        venue_id=venues.get_venue_id(venue) if venue else None,
        venue_name=venue,
        venue_sort=venue_sort,
        date_start=date_start,
        assets="[]",
        data=models.Show(
            id=show_id,
            title=title,
            season="In House",
            venue=venue,
            venue_sort=venue_sort,
        ).model_dump_json(),
    )


def make_venue(venue_id: str, name: str, **data) -> database.Venue:
    return database.Venue.create(
        id=venue_id,
        name=name,
        data=models.Venue(title=name, **data).model_dump_json(),
        content=f"<p>About the {name}.</p>",
    )


@pytest.fixture()
def populated_db(test_db):
    make_venue(
        "new-theatre",
        "New Theatre",
        built=NEW_THEATRE_BUILT,
        city="Nottingham",
        images=["nQTq7s8", "Xnt862b"],
    )
    make_venue("c-venues", "C venues", city="Edinburgh")
    make_show("1999-00/main_show", "Main Show", "New Theatre", date_start="1999-10-01")
    make_show("1999-00/late_show", "Late Show", "New Theatre", date_start="2000-01-01")
    make_show(
        "1999-00/fringe_show",
        "Fringe Show",
        "C soco",
        venue_sort="C venues",
        date_start="1999-08-01",
    )
    make_show(
        "1999-00/other_fringe_show",
        "Other Fringe Show",
        "C soco",
        venue_sort="C venues",
        date_start="1999-08-02",
    )
    make_show("1999-00/mystery_show", "Mystery Show", "unknown")
    make_show("1999-00/online_show", "Online Show", "YouTube", venue_sort="Online")
    make_show("1999-00/venueless_show", "Venueless Show", None)
    return test_db


@pytest.fixture()
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(dumper, "OUTPUT_DIR", tmp_path)
    return tmp_path


def dump_venues(output_dir: Path) -> Path:
    dumper.dump_venues(state=DumperSharedState(search_documents=[]))
    return output_dir / "venues"


def read_json(path: Path):
    return json.loads(path.read_text())


def get_record(venue_id: str) -> venues.VenueRecord:
    return next(
        record for record in venues.get_venue_records() if record.id == venue_id
    )


class TestVenueRecords:
    def test_every_referenced_venue_has_a_record(self, populated_db):
        assert [record.id for record in venues.get_venue_records()] == [
            "c-soco",
            "c-venues",
            "new-theatre",
            "unknown",
            "youtube",
        ]

    def test_filed_venue_has_record(self, populated_db):
        assert get_record("new-theatre").has_record is True

    def test_referenced_only_venue_is_a_stub(self, populated_db):
        stub = get_record("c-soco")
        assert stub.has_record is False
        assert stub.name == "C soco"

    def test_filed_venue_without_shows_is_kept(self, populated_db):
        assert get_record("c-venues").shows == []

    def test_show_without_venue_is_in_no_record(self, populated_db):
        show_ids = {
            show.id for record in venues.get_venue_records() for show in record.shows
        }
        assert "1999-00/venueless_show" not in show_ids

    def test_shows_are_in_date_order(self, populated_db):
        assert [show.id for show in get_record("new-theatre").shows] == [
            "1999-00/main_show",
            "1999-00/late_show",
        ]


class TestStubNames:
    def test_most_common_spelling_wins(self, test_db):
        make_show("1999-00/one", "One", "The Zoo")
        make_show("1999-00/two", "Two", "The zoo")
        make_show("1999-00/three", "Three", "The Zoo")
        assert get_record("the-zoo").name == "The Zoo"

    def test_divergent_spellings_are_logged(
        self, test_db, caplog: pytest.LogCaptureFixture
    ):
        make_show("1999-00/one", "One", "The Zoo")
        make_show("1999-00/two", "Two", "The zoo")
        with caplog.at_level(logging.WARNING):
            get_record("the-zoo")
        assert "the-zoo" in caplog.text
        assert "The zoo" in caplog.text


class TestSentinelVenues:
    def test_unknown_is_a_named_sentinel(self, populated_db):
        record = get_record("unknown")
        assert record.sentinel is True
        assert record.name == "Venue unknown"
        assert record.has_record is False

    def test_youtube_is_a_named_sentinel(self, populated_db):
        record = get_record("youtube")
        assert record.sentinel is True
        assert record.name == "Online — YouTube"

    def test_ordinary_venue_is_not_a_sentinel(self, populated_db):
        assert get_record("new-theatre").sentinel is False


class TestVenueSort:
    def test_venue_sort_ingested_from_show_frontmatter(self):
        show = models.Show(
            id="a_show", title="A Show", season="In House", venue_sort="C venues"
        )
        assert show.venue_sort == "C venues"

    def test_venue_takes_venue_sort_from_its_shows(self, populated_db):
        assert get_record("c-soco").venue_sort == "C venues"

    def test_venue_without_venue_sort_has_none(self, populated_db):
        assert get_record("new-theatre").venue_sort is None

    def test_most_common_venue_sort_wins(self, test_db):
        make_show("1999-00/one", "One", "C soco", venue_sort="C venues")
        make_show("1999-00/two", "Two", "C soco", venue_sort="C venues")
        make_show("1999-00/three", "Three", "C soco", venue_sort="Edinburgh")
        assert get_record("c-soco").venue_sort == "C venues"


class TestVenueAssets:
    def test_images_become_assets(self, populated_db):
        detail = venues.get_venue_detail(get_record("new-theatre"))
        assert [asset.id for asset in detail.assets] == ["nQTq7s8", "Xnt862b"]
        assert detail.assets[0].type == "image"
        assert detail.assets[0].source == "smugmug"

    def test_stub_has_no_assets(self, populated_db):
        assert venues.get_venue_detail(get_record("c-soco")).assets == []

    def test_assets_carry_smugmug_dimensions(self, populated_db):
        saved_asset = assets.save_asset(
            target_id="new-theatre",
            target_type=assets.AssetTarget.VENUE,
            source=assets.AssetSource.SMUGMUG,
            type=assets.AssetType.IMAGE,
            id="nQTq7s8",
        )
        saved_asset.asset_smugmug_data = SmugMugImageInfo(
            width=1024, height=768
        ).model_dump_json()
        saved_asset.save()
        assets.get_smugmug_image_info_map.cache_clear()
        detail = venues.get_venue_detail(get_record("new-theatre"))
        assets.get_smugmug_image_info_map.cache_clear()
        assert (detail.assets[0].width, detail.assets[0].height) == (1024, 768)


class TestDumpVenues:
    def test_index_lists_every_venue(self, populated_db, output_dir: Path):
        index = read_json(dump_venues(output_dir) / "index.json")
        assert [venue["id"] for venue in index] == [
            "c-soco",
            "c-venues",
            "new-theatre",
            "unknown",
            "youtube",
        ]

    def test_index_carries_stub_and_sentinel_flags(
        self, populated_db, output_dir: Path
    ):
        index = read_json(dump_venues(output_dir) / "index.json")
        flags = {
            venue["id"]: (venue["hasRecord"], venue["sentinel"]) for venue in index
        }
        assert flags == {
            "c-soco": (False, False),
            "c-venues": (True, False),
            "new-theatre": (True, False),
            "unknown": (False, True),
            "youtube": (False, True),
        }

    def test_index_carries_the_venue_group(self, populated_db, output_dir: Path):
        index = read_json(dump_venues(output_dir) / "index.json")
        c_soco = next(venue for venue in index if venue["id"] == "c-soco")
        assert c_soco["group"] == "C venues"

    def test_stub_detail_carries_shows_and_no_details(
        self, populated_db, output_dir: Path
    ):
        stub = read_json(dump_venues(output_dir) / "c-soco.json")
        assert stub["name"] == "C soco"
        assert stub["showCount"] == len(C_SOCO_SHOW_IDS)
        assert [show["id"] for show in stub["shows"]] == C_SOCO_SHOW_IDS
        assert {"built", "location", "city", "content"}.isdisjoint(stub)

    def test_sentinel_detail_dumped(self, populated_db, output_dir: Path):
        sentinel = read_json(dump_venues(output_dir) / "unknown.json")
        assert sentinel["name"] == "Venue unknown"
        assert sentinel["sentinel"] is True
        assert [show["id"] for show in sentinel["shows"]] == ["1999-00/mystery_show"]

    def test_filed_detail_carries_document_fields(self, populated_db, output_dir: Path):
        detail = read_json(dump_venues(output_dir) / "new-theatre.json")
        assert detail["built"] == NEW_THEATRE_BUILT
        assert detail["city"] == "Nottingham"
        assert detail["content"] == "<p>About the New Theatre.</p>"
        assert [asset["id"] for asset in detail["assets"]] == ["nQTq7s8", "Xnt862b"]


class TestVenueSpec:
    def test_paths_present(self):
        assert (
            spec.SPEC["paths"]["/venues/index.json"]["get"]["operationId"]
            == "getVenueList"
        )
        assert (
            spec.SPEC["paths"]["/venues/{id}.json"]["get"]["operationId"]
            == "getVenueDetail"
        )

    def test_models_carry_stub_fields(self):
        for model in ("VenueList", "VenueDetail"):
            properties = spec.SPEC["components"]["schemas"][model]["properties"]
            assert {"hasRecord", "sentinel", "group"} <= set(properties), model

    def test_detail_carries_assets(self):
        assert (
            "assets" in spec.SPEC["components"]["schemas"]["VenueDetail"]["properties"]
        )
