import json
import logging
from pathlib import Path

import pytest

from nthp_api.nthp_build import (
    database,
    dumper,
    models,
    schema,
    seasons,
    shows,
    spec,
)
from nthp_api.nthp_build.parallel import DumperSharedState


@pytest.mark.parametrize(
    ("season_name", "expected"),
    [
        ("In House", "in-house"),
        ("StuFF", "stuff"),
        ("Studio", "studio"),
        ("IUDF", "iudf"),
        ("BedFest", "bedfest"),
        ("Unknown", "unknown"),
        ("Fred's Season", "freds-season"),
        ("Spring - Summer", "spring-summer"),
    ],
)
def test_slugify_season_name(season_name: str, expected: str):
    assert seasons.slugify_season_name(season_name) == expected


@pytest.mark.parametrize(
    ("season_name", "expected"),
    [
        ("In House", "in-house"),
        ("UNCUT", "studio"),
        ("Fringe", "studio"),
        ("Studio", "studio"),
        ("Unscripted", "creatives"),
        ("Creatives", "creatives"),
        ("unknown", "unknown"),
    ],
)
def test_get_show_season_id(season_name: str, expected: str):
    assert seasons.get_show_season_id(season_name, "_shows/99_00/a_show.md") == expected


def test_get_show_season_id_unrecognised_logs_error(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.ERROR):
        season_id = seasons.get_show_season_id(
            "Interpretive Dance", "_shows/99_00/a_show.md"
        )
    assert season_id is None
    assert "Interpretive Dance" in caplog.text
    assert "_shows/99_00/a_show.md" in caplog.text


def test_every_season_id_is_unique():
    season_ids = [
        seasons.get_season_id(definition) for definition in seasons.SEASON_DEFINITIONS
    ]
    assert len(season_ids) == len(set(season_ids))


def test_unknown_season_is_a_definition():
    assert seasons.get_show_season_id("unknown", "a_show.md") == "unknown"
    assert seasons.SEASON_DEFINITION_MAP["unknown"].name == "Unknown"


def make_show(
    show_id: str, title: str, season: str, date_start: str | None = None
) -> database.Show:
    return database.Show.create(
        id=show_id,
        source_path=f"_shows/{show_id}.md",
        year=1999,
        year_id="1999-00",
        title=title,
        season_id=seasons.get_show_season_id(season, f"_shows/{show_id}.md"),
        date_start=date_start,
        assets="[]",
        data=models.Show(id=show_id, title=title, season=season).model_dump_json(),
    )


@pytest.fixture()
def populated_db(test_db):
    """One show per merged name, so the Studio season should gather all three."""
    make_show("1999-00/uncut_show", "Uncut Show", "UNCUT", "1999-10-01")
    make_show("1999-00/fringe_show", "Fringe Show", "Fringe", "1999-11-01")
    make_show("1999-00/studio_show", "Studio Show", "Studio", "1999-12-01")
    make_show("1999-00/in_house_show", "In House Show", "In House", "2000-01-01")
    make_show("1999-00/mystery_show", "Mystery Show", "unknown", "2000-02-01")
    make_show("1999-00/odd_show", "Odd Show", "Interpretive Dance", "2000-03-01")
    return test_db


@pytest.fixture()
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(dumper, "OUTPUT_DIR", tmp_path)
    return tmp_path


def dump_seasons(output_dir: Path) -> Path:
    dumper.dump_seasons(state=DumperSharedState(search_documents=[]))
    return output_dir / "seasons"


def read_json(path: Path):
    return json.loads(path.read_text())


STUDIO_SHOW_IDS = [
    "1999-00/uncut_show",
    "1999-00/fringe_show",
    "1999-00/studio_show",
]


class TestShowSeasonId:
    def test_merged_shows_share_a_season_id(self, populated_db):
        studio_show_ids = {
            show.id
            for show in database.Show.select().where(
                database.Show.season_id == "studio"
            )
        }
        assert studio_show_ids == set(STUDIO_SHOW_IDS)

    def test_unrecognised_season_still_loads_show(self, populated_db):
        odd_show = database.Show.get_by_id("1999-00/odd_show")
        assert odd_show.season_id is None

    def test_show_list_item_carries_season_id(self, populated_db):
        show_list_item = shows.get_show_list_item(
            database.Show.get_by_id("1999-00/uncut_show")
        )
        assert show_list_item.season == "UNCUT"
        assert show_list_item.season_id == "studio"

    def test_show_detail_carries_season_id(self, populated_db):
        show_detail = shows.get_show_detail(
            database.Show.get_by_id("1999-00/in_house_show")
        )
        assert show_detail.season_id == "in-house"


class TestDumpSeasons:
    def test_index_lists_every_season(self, populated_db, output_dir: Path):
        index = read_json(dump_seasons(output_dir) / "index.json")
        assert [season["id"] for season in index] == [
            seasons.get_season_id(definition)
            for definition in seasons.SEASON_DEFINITIONS
        ]

    def test_index_counts_merged_shows(self, populated_db, output_dir: Path):
        index = read_json(dump_seasons(output_dir) / "index.json")
        show_counts = {season["id"]: season["showCount"] for season in index}
        assert show_counts == {
            **{
                seasons.get_season_id(definition): 0
                for definition in seasons.SEASON_DEFINITIONS
            },
            "studio": len(STUDIO_SHOW_IDS),
            "in-house": 1,
            "unknown": 1,
        }

    def test_index_lists_aliases(self, populated_db, output_dir: Path):
        index = read_json(dump_seasons(output_dir) / "index.json")
        studio = next(season for season in index if season["id"] == "studio")
        assert studio["name"] == "Studio"
        assert studio["aliases"] == ["Fringe", "UNCUT"]

    def test_unknown_season_dumped_as_a_record(self, populated_db, output_dir: Path):
        unknown = read_json(dump_seasons(output_dir) / "unknown.json")
        assert unknown["name"] == "Unknown"
        assert [show["id"] for show in unknown["shows"]] == ["1999-00/mystery_show"]

    def test_detail_shows_in_date_order(self, populated_db, output_dir: Path):
        studio = read_json(dump_seasons(output_dir) / "studio.json")
        assert [show["id"] for show in studio["shows"]] == STUDIO_SHOW_IDS

    def test_show_with_unrecognised_season_is_in_no_season(
        self, populated_db, output_dir: Path
    ):
        season_dir = dump_seasons(output_dir)
        dumped_show_ids = {
            show["id"]
            for path in season_dir.glob("*.json")
            if path.name != "index.json"
            for show in read_json(path)["shows"]
        }
        assert "1999-00/odd_show" not in dumped_show_ids


class TestSeasonSpec:
    def test_paths_present(self):
        assert (
            spec.SPEC["paths"]["/seasons/index.json"]["get"]["operationId"]
            == "getSeasonIndex"
        )
        assert (
            spec.SPEC["paths"]["/seasons/{id}.json"]["get"]["operationId"]
            == "getSeasonDetail"
        )

    def test_models_present(self):
        assert set(spec.SPEC["components"]["schemas"]["SeasonList"]["properties"]) == {
            "id",
            "name",
            "aliases",
            "showCount",
        }
        assert (
            "shows" in spec.SPEC["components"]["schemas"]["SeasonDetail"]["properties"]
        )

    def test_show_schemas_carry_season_id(self):
        for model in ("ShowList", "ShowDetail"):
            assert (
                "seasonId" in spec.SPEC["components"]["schemas"][model]["properties"]
            ), model


def test_season_list_matches_schema(populated_db):
    definition = seasons.SEASON_DEFINITION_MAP["Studio"]
    season_list = seasons.get_season_list(
        definition, seasons.get_season_shows("studio")
    )
    assert season_list == schema.SeasonList(
        id="studio",
        name="Studio",
        aliases=["Fringe", "UNCUT"],
        show_count=len(STUDIO_SHOW_IDS),
    )
