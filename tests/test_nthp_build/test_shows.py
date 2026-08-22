import json
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
    venues,
    years,
)
from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.parallel import DumperSharedState


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            {
                "playwright": "William Shakespeare",
                "devised": False,
                "improvised": False,
            },
            schema.PlaywrightShow(
                id="william_shakespeare",
                type=schema.PlaywrightType.PLAYWRIGHT,
                name="William Shakespeare",
                descriptor="by William Shakespeare",
                student_written=False,
                person_id=None,
            ),
        ),
        (
            {
                "playwright": "Fred Bloggs",
                "devised": False,
                "improvised": False,
                "student_written": True,
            },
            schema.PlaywrightShow(
                id="fred_bloggs",
                type=schema.PlaywrightType.PLAYWRIGHT,
                name="Fred Bloggs",
                descriptor="by Fred Bloggs",
                student_written=True,
                person_id="fred_bloggs",
            ),
        ),
        (
            {"playwright": "unknown", "devised": False, "improvised": False},
            schema.PlaywrightShow(
                type=schema.PlaywrightType.UNKNOWN,
                descriptor="Unknown",
                student_written=False,
            ),
        ),
        (
            {"playwright": "Various", "devised": False, "improvised": False},
            schema.PlaywrightShow(
                type=schema.PlaywrightType.VARIOUS,
                descriptor="Various Writers",
                student_written=False,
            ),
        ),
        (
            {"playwright": None, "devised": True, "improvised": False},
            schema.PlaywrightShow(
                type=schema.PlaywrightType.DEVISED,
                descriptor="Devised",
                student_written=False,
            ),
        ),
        (
            {"playwright": None, "devised": "Someone", "improvised": False},
            schema.PlaywrightShow(
                type=schema.PlaywrightType.DEVISED,
                descriptor="Devised by Someone",
                student_written=False,
            ),
        ),
        (
            {
                "playwright": None,
                "devised": "Cast",
                "improvised": False,
                "student_written": True,
            },
            schema.PlaywrightShow(
                type=schema.PlaywrightType.DEVISED,
                descriptor="Devised by Cast",
                student_written=True,
            ),
        ),
        (
            {"playwright": None, "devised": False, "improvised": True},
            schema.PlaywrightShow(
                type=schema.PlaywrightType.IMPROVISED,
                descriptor="Improvised",
                student_written=False,
            ),
        ),
        (
            {"playwright": None, "devised": False, "improvised": False},
            None,
        ),
    ],
)
def test_get_show_playwright(input: dict, expected: schema.PlaywrightShow):
    show = models.Show.model_construct(**input)
    assert shows.get_show_playwright(show) == expected


def make_show(  # noqa: PLR0913, PLR0917
    show_id: str,
    title: str = "A Show",
    year: int = 1999,
    season: str = "In House",
    season_sort: int | None = None,
    date_start: str | None = None,
    primary_image: str | None = None,
    content: str | None = "<p>A synopsis</p>",
    **show_fields,
) -> database.Show:
    year_id = years.get_public_year_id(year)
    return database.Show.create(
        id=f"{year_id}/{show_id}",
        source_path=f"_shows/{show_id}.md",
        year=year,
        year_id=year_id,
        title=title,
        venue_id=venues.get_venue_id(show_fields["venue"])
        if show_fields.get("venue")
        else None,
        venue_name=show_fields.get("venue"),
        season_id=seasons.get_show_season_id(season, f"_shows/{show_id}.md"),
        season_sort=season_sort,
        date_start=date_start,
        primary_image=primary_image,
        assets="[]",
        content=content,
        data=models.Show(
            id=show_id,
            title=title,
            season=season,
            season_sort=season_sort,
            **show_fields,
        ).model_dump_json(),
    )


def make_person_refs(count: int) -> list[dict]:
    return [
        {"role": f"Role {index}", "name": f"Person {index}"} for index in range(count)
    ]


@pytest.fixture()
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(dumper, "OUTPUT_DIR", tmp_path)
    return tmp_path


def dump_shows(output_dir: Path) -> Path:
    dumper.dump_shows(state=DumperSharedState(search_documents=[]))
    return output_dir / "shows"


def read_json(path: Path):
    return json.loads(path.read_text())


@pytest.fixture()
def sequenced_db(test_db):
    """Shows out of order, so only the canonical ordering puts them back."""
    make_show(
        "second", title="Second", year=2000, season_sort=200, date_start="2001-03-01"
    )
    make_show(
        "first", title="First", year=2000, season_sort=100, date_start="2001-04-01"
    )
    make_show("third", title="Third", year=2000, date_start="2001-05-01")
    make_show(
        "earlier", title="Earlier", year=1999, season_sort=900, date_start="2000-06-01"
    )
    return test_db


ORDERED_SHOW_IDS = [
    "1999-00/earlier",
    "2000-01/first",
    "2000-01/second",
    "2000-01/third",
]


class TestShowOrder:
    def test_year_beats_season_sort(self, sequenced_db):
        assert [show.id for show in shows.get_show_query()] == ORDERED_SHOW_IDS

    def test_shows_without_season_sort_end_the_year(self, sequenced_db):
        assert [show.id for show in shows.get_show_query()][-1] == "2000-01/third"

    def test_ties_break_on_id(self, test_db):
        make_show("beta", year=2000)
        make_show("alpha", year=2000)
        assert [show.id for show in shows.get_show_query()] == [
            "2000-01/alpha",
            "2000-01/beta",
        ]


class TestShowIndex:
    def test_index_is_in_canonical_order(self, sequenced_db, output_dir: Path):
        index = read_json(dump_shows(output_dir) / "index.json")
        assert [item["id"] for item in index] == ORDERED_SHOW_IDS

    def test_index_item_carries_year_season_and_playwright(
        self, test_db, output_dir: Path
    ):
        make_show(
            "macbeth",
            title="Macbeth",
            year=2000,
            season="UNCUT",
            date_start="2001-02-03",
            primary_image="XYZ",
            playwright="William Shakespeare",
            venue="New Theatre",
        )
        index = read_json(dump_shows(output_dir) / "index.json")
        assert index == [
            {
                "id": "2000-01/macbeth",
                "title": "Macbeth",
                "yearId": "2000-01",
                "year": 2000,
                "season": "UNCUT",
                "seasonId": "studio",
                "venue": {"id": "new-theatre", "name": "New Theatre"},
                "dateStart": "2001-02-03",
                "primaryImage": "XYZ",
                "playwrightDescriptor": "by William Shakespeare",
            }
        ]


class TestShowSequence:
    def test_neighbours_span_the_whole_archive(self, sequenced_db, output_dir: Path):
        show_dir = dump_shows(output_dir)
        first_of_2000 = read_json(show_dir / "2000-01" / "first.json")
        assert first_of_2000["previous"]["id"] == "1999-00/earlier"
        assert first_of_2000["next"]["id"] == "2000-01/second"

    def test_ends_of_the_archive_have_no_neighbour(
        self, sequenced_db, output_dir: Path
    ):
        show_dir = dump_shows(output_dir)
        assert "previous" not in read_json(show_dir / "1999-00" / "earlier.json")
        assert "next" not in read_json(show_dir / "2000-01" / "third.json")

    def test_neighbour_carries_title_and_image(self, test_db, output_dir: Path):
        make_show("one", title="One", season_sort=10)
        make_show("two", title="Two", season_sort=20, primary_image="XYZ")
        show_dir = dump_shows(output_dir)
        assert read_json(show_dir / "1999-00" / "one.json")["next"] == {
            "id": "1999-00/two",
            "title": "Two",
            "primaryImage": "XYZ",
        }


class TestMissingFields:
    def test_a_complete_show_misses_nothing(self, test_db):
        make_show(
            "complete",
            date_start="2000-01-01",
            primary_image="XYZ",
            venue="New Theatre",
            playwright="William Shakespeare",
            cast=make_person_refs(2),
            crew=make_person_refs(6),
        )
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/complete"))
        assert show_detail.missing_fields == []

    def test_a_bare_show_misses_everything(self, test_db):
        make_show("bare", content=None)
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/bare"))
        assert show_detail.missing_fields == [
            schema.ShowMissingField.DATE_START,
            schema.ShowMissingField.POSTER,
            schema.ShowMissingField.EXCERPT,
            schema.ShowMissingField.CAST,
            schema.ShowMissingField.CREW,
            schema.ShowMissingField.PLAYWRIGHT,
            schema.ShowMissingField.VENUE,
        ]

    def test_incomplete_cast_counts_over_missing_cast(self, test_db):
        make_show("show", cast=make_person_refs(2), cast_incomplete=True)
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert schema.ShowMissingField.CAST_INCOMPLETE in show_detail.missing_fields
        assert schema.ShowMissingField.CAST not in show_detail.missing_fields

    def test_a_low_crew_count_is_short_not_missing(self, test_db):
        make_show("show", crew=make_person_refs(settings.show_low_crew))
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert schema.ShowMissingField.CREW_SHORT in show_detail.missing_fields
        assert schema.ShowMissingField.CREW not in show_detail.missing_fields

    def test_crew_above_the_threshold_is_not_short(self, test_db):
        make_show("show", crew=make_person_refs(settings.show_low_crew + 1))
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert schema.ShowMissingField.CREW_SHORT not in show_detail.missing_fields

    def test_an_unknown_playwright_is_missing(self, test_db):
        make_show("show", playwright="unknown")
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert schema.ShowMissingField.PLAYWRIGHT in show_detail.missing_fields

    def test_a_devised_show_has_a_playwright(self, test_db):
        make_show("show", devised=True)
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert schema.ShowMissingField.PLAYWRIGHT not in show_detail.missing_fields


class TestIgnoreMissing:
    def test_authored_ignore_missing_is_carried(self, test_db):
        make_show("show", ignore_missing=True)
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert show_detail.ignore_missing is True
        assert show_detail.ignore_missing_in_seasons is False

    def test_a_season_that_ignores_missing_is_flagged(self, test_db):
        make_show("show", season="StuFF")
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert show_detail.ignore_missing is False
        assert show_detail.ignore_missing_in_seasons is True

    def test_a_documented_season_is_not_flagged(self, test_db):
        make_show("show", season="In House")
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert show_detail.ignore_missing_in_seasons is False


class TestTour:
    def test_tour_dates_are_output(self, test_db):
        make_show(
            "show",
            tour=[
                {
                    "venue": "NSDF 2019",
                    "date_start": "2019-04-17",
                    "date_end": "2019-04-18",
                    "notes": "Award for someone",
                    "comment": "An editorial aside",
                }
            ],
        )
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert show_detail.tour == [
            schema.ShowTourDate(
                venue="NSDF 2019",
                date_start="2019-04-17",
                date_end="2019-04-18",
                note="Award for someone",
            )
        ]

    def test_a_show_without_a_tour_has_none(self, test_db):
        make_show("show")
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert show_detail.tour == []


class TestCompanySort:
    def test_company_sort_is_ingested_but_not_output(self, test_db):
        make_show("show", company="A Company", company_sort="Company, A")
        show_inst = database.Show.get_by_id("1999-00/show")
        assert models.Show(**json.loads(show_inst.data)).company_sort == "Company, A"
        assert "companySort" not in shows.get_show_detail(show_inst).model_dump(
            by_alias=True
        )


def test_show_index_is_in_the_spec():
    assert "/shows/index.json" in spec.SPEC["paths"]
