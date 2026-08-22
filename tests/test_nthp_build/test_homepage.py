import json
from pathlib import Path

import pytest

from nthp_api.nthp_build import database, dumper, homepage, models, schema, spec, years
from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.fields import FuzzyDate
from nthp_api.nthp_build.parallel import DumperSharedState

DAYS_IN_LEAP_YEAR = 366


def make_show(  # noqa: PLR0913, PLR0917
    show_id: str,
    title: str = "A Show",
    year: int = 1999,
    date_start: str | None = None,
    date_end: str | None = None,
    primary_image: str | None = None,
    season_sort: int | None = None,
) -> database.Show:
    year_id = years.get_public_year_id(year)
    return database.Show.create(
        id=f"{year_id}/{show_id}",
        source_path=f"_shows/{show_id}.md",
        year=year,
        year_id=year_id,
        title=title,
        season_id="in-house",
        season_sort=season_sort,
        date_start=date_start,
        date_end=date_end,
        primary_image=primary_image,
        assets="[]",
        data=models.Show(id=show_id, title=title, season="In House").model_dump_json(),
    )


@pytest.fixture()
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(dumper, "OUTPUT_DIR", tmp_path)
    return tmp_path


def read_json(path: Path):
    return json.loads(path.read_text())


class TestDaysOfYear:
    def test_covers_a_leap_year(self):
        assert len(homepage.get_days_of_year()) == DAYS_IN_LEAP_YEAR

    def test_includes_the_leap_day(self):
        assert (2, 29) in homepage.get_days_of_year()

    def test_id_is_zero_padded(self):
        assert homepage.get_day_of_year_id((2, 29)) == "02-29"


class TestRunDaysOfYear:
    def test_single_day(self):
        assert homepage.get_run_days_of_year(FuzzyDate(1999, 11, 13), None) == {
            (11, 13)
        }

    def test_spans_a_month_boundary(self):
        assert homepage.get_run_days_of_year(
            FuzzyDate(2001, 2, 28), FuzzyDate(2001, 3, 3)
        ) == {(2, 28), (3, 1), (3, 2), (3, 3)}

    def test_includes_the_leap_day(self):
        assert (2, 29) in homepage.get_run_days_of_year(
            FuzzyDate(2012, 2, 29), FuzzyDate(2012, 3, 3)
        )

    def test_skips_the_leap_day_outside_a_leap_year(self):
        assert (2, 29) not in homepage.get_run_days_of_year(
            FuzzyDate(2011, 2, 28), FuzzyDate(2011, 3, 1)
        )

    def test_wraps_the_year(self):
        assert homepage.get_run_days_of_year(
            FuzzyDate(1999, 12, 30), FuzzyDate(2000, 1, 2)
        ) == {(12, 30), (12, 31), (1, 1), (1, 2)}


class TestShowRun:
    def test_day_precision_start(self, test_db):
        show_inst = make_show("macbeth", date_start="1999-11-13")
        assert homepage.get_show_run(show_inst) == (FuzzyDate(1999, 11, 13), None)

    def test_undated_show_has_no_run(self, test_db):
        assert homepage.get_show_run(make_show("macbeth")) is None

    def test_month_precision_show_has_no_run(self, test_db):
        assert homepage.get_show_run(make_show("macbeth", date_start="1999-11")) is None

    def test_end_before_start_falls_back_to_the_start(self, test_db):
        show_inst = make_show("macbeth", date_start="2007-03-20", date_end="2007-03-13")
        assert homepage.get_show_run(show_inst) == (FuzzyDate(2007, 3, 20), None)


class TestShowsByDayOfYear:
    def test_show_runs_on_every_day_of_its_run(self, test_db):
        make_show("macbeth", date_start="2001-02-28", date_end="2001-03-03")
        shows_by_day = homepage.get_shows_by_day_of_year()
        assert [show.id for show in shows_by_day[(2, 28)]] == ["1999-00/macbeth"]
        assert [show.id for show in shows_by_day[(3, 1)]] == ["1999-00/macbeth"]
        assert [show.id for show in shows_by_day[(3, 4)]] == []

    def test_ordered_by_year(self, test_db):
        make_show("later", year=2001, date_start="2001-11-13")
        make_show("earlier", year=1999, date_start="1999-11-13")
        shows_by_day = homepage.get_shows_by_day_of_year()
        assert [show.year for show in shows_by_day[(11, 13)]] == [1999, 2001]

    def test_month_precision_show_left_out(self, test_db):
        make_show("macbeth", date_start="1999-11")
        assert homepage.get_shows_by_day_of_year() == {}


class TestDumpOnThisDay:
    @pytest.fixture()
    def dumped(self, test_db, output_dir: Path) -> Path:
        make_show(
            "the_gut_girls",
            title="The Gut Girls",
            year=2011,
            date_start="2012-02-29",
            date_end="2012-03-03",
            primary_image="abc12",
        )
        dumper.dump_on_this_day(state=DumperSharedState(search_documents=[]))
        return output_dir / "on-this-day"

    def test_writes_a_file_for_every_day(self, dumped: Path):
        assert len(list(dumped.glob("*.json"))) == DAYS_IN_LEAP_YEAR

    def test_leap_day_holds_the_show(self, dumped: Path):
        assert read_json(dumped / "02-29.json") == [
            {
                "id": "2011-12/the_gut_girls",
                "title": "The Gut Girls",
                "yearId": "2011-12",
                "year": 2011,
                "primaryImage": {"id": "abc12"},
                "dateStart": "2012-02-29",
                "dateEnd": "2012-03-03",
            }
        ]

    def test_run_spans_the_month_boundary(self, dumped: Path):
        assert [show["id"] for show in read_json(dumped / "03-01.json")] == [
            "2011-12/the_gut_girls"
        ]

    def test_days_with_nothing_running_are_empty(self, dumped: Path):
        assert read_json(dumped / "07-01.json") == []


class TestPosters:
    def test_only_shows_with_an_image(self, test_db):
        make_show("macbeth", primary_image="abc12")
        make_show("hamlet")
        assert [item.id for item in homepage.get_poster_items()] == ["1999-00/macbeth"]

    def test_canonical_show_order(self, test_db):
        make_show("later", year=2001, primary_image="def34")
        make_show("earlier", year=1999, primary_image="abc12")
        assert [item.id for item in homepage.get_poster_items()] == [
            "1999-00/earlier",
            "2001-02/later",
        ]

    def test_dumped_fields(self, test_db, output_dir: Path):
        make_show("macbeth", title="Macbeth", primary_image="abc12")
        dumper.dump_posters(state=DumperSharedState(search_documents=[]))
        assert read_json(output_dir / "assets" / "posters.json") == [
            {
                "id": "1999-00/macbeth",
                "title": "Macbeth",
                "yearId": "1999-00",
                "year": 1999,
                "primaryImage": {"id": "abc12"},
            }
        ]


class TestSiteStats:
    @pytest.fixture()
    def stats(self, test_db, output_dir: Path) -> dict:
        make_show("macbeth", primary_image="abc12")
        make_show("hamlet")
        database.Venue.create(
            id="new-theatre",
            name="New Theatre",
            data=models.Venue(title="New Theatre").model_dump_json(),
        )
        database.Person.create(
            id="fred_bloggs", title="Fred Bloggs", headshot="abc12", data="{}"
        )
        database.Person.create(id="jane_doe", title="Jane Doe", data="{}")
        dumper.dump_site_stats(state=DumperSharedState(search_documents=[]))
        return read_json(output_dir / "index.json")

    def test_shows_with_image_count(self, stats: dict):
        assert stats["showWithImageCount"] == 1

    def test_person_with_headshot_count(self, stats: dict):
        assert stats["personWithHeadshotCount"] == 1

    def test_venue_count(self, stats: dict):
        assert stats["venueCount"] == 1

    def test_year_count(self, stats: dict):
        assert stats["yearCount"] == settings.year_end - settings.year_start

    def test_year_bounds(self, stats: dict):
        assert stats["firstYearId"] == years.get_public_year_id(settings.year_start)
        assert stats["latestYearId"] == years.get_public_year_id(settings.year_end - 1)


class TestSpec:
    def test_on_this_day_takes_a_date_parameter(self):
        operation = spec.SPEC["paths"]["/on-this-day/{date}.json"]["get"]
        assert [parameter["name"] for parameter in operation["parameters"]] == ["date"]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("OnThisDayShowCollection")

    def test_posters_path(self):
        operation = spec.SPEC["paths"]["/assets/posters.json"]["get"]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("PosterCollection")

    def test_site_stats_carries_the_new_counts(self):
        properties = spec.SPEC["components"]["schemas"]["SiteStats"]["properties"]
        assert {
            "venueCount",
            "yearCount",
            "firstYearId",
            "latestYearId",
            "showWithImageCount",
            "personWithHeadshotCount",
        } <= set(properties)


def test_venue_count_counts_referenced_venues(test_db, output_dir: Path):
    """A venue a show merely names counts, as the venue index has it."""
    show_inst = make_show("macbeth")
    show_inst.venue_id = "new-theatre"
    show_inst.venue_name = "New Theatre"
    show_inst.save()
    dumper.dump_site_stats(state=DumperSharedState(search_documents=[]))
    assert read_json(output_dir / "index.json")["venueCount"] == 1


def test_on_this_day_show_requires_a_start_date():
    with pytest.raises(ValueError, match="dateStart"):
        schema.OnThisDayShow(id="a", title="A", year_id="1999-00", year=1999)  # type: ignore[call-arg]
