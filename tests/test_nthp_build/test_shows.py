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
            {
                "playwright": "NNT Creatives",
                "devised": False,
                "improvised": False,
                "student_written": True,
            },
            schema.PlaywrightShow(
                id="nnt_creatives",
                type=schema.PlaywrightType.PLAYWRIGHT,
                name="NNT Creatives",
                descriptor="by NNT Creatives",
                student_written=True,
                person_id=None,
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
                "primaryImage": {"id": "XYZ"},
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
            "yearId": "1999-00",
            "year": 1999,
            "primaryImage": {"id": "XYZ"},
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


class TestStudentPlaywrightCredit:
    @staticmethod
    def make_show(**kwargs) -> models.Show:
        return models.Show(
            **{"id": "a_show", "title": "A Show", "season": "In House", **kwargs}
        )

    def test_mixy_credits_the_alias(self):
        """content/_shows/22_23/mixy.md, written under a stage name."""
        show = self.make_show(
            title="Mixy",
            playwright="Sunenna Kaur",
            playwright_alias="Sunenna Sohal",
            student_written=True,
            crew=[models.PersonRef(role="Director", name="Sunenna Sohal")],
        )
        assert shows.get_crew_with_student_playwright(
            show, Path("_shows/00_01/a_show.md")
        ) == [
            models.PersonRef(role="Playwright", name="Sunenna Sohal"),
            models.PersonRef(role="Director", name="Sunenna Sohal"),
        ]

    def test_the_great_gatsby_credits_the_adaptor(self):
        """content/_shows/16_17/the_great_gatsby.md, a student adaptation."""
        show = self.make_show(
            title="The Great Gatsby",
            playwright="F. Scott Fitzgerald",
            adaptor="L. J. Bateman",
            playwright_alias="Laura Jayne Bateman",
            student_written=True,
            crew=[models.PersonRef(role="Director", name="Laura Jayne Bateman")],
        )
        assert shows.get_crew_with_student_playwright(
            show, Path("_shows/00_01/a_show.md")
        )[0] == models.PersonRef(role="Adaptor", name="Laura Jayne Bateman")

    def test_translator_credited_where_there_is_no_adaptor(self):
        show = self.make_show(
            playwright="Anton Chekhov",
            translator="Fred Bloggs",
            student_written=True,
        )
        assert shows.get_crew_with_student_playwright(
            show, Path("_shows/00_01/a_show.md")
        ) == [models.PersonRef(role="Translator", name="Fred Bloggs")]

    def test_playwright_credited_without_an_alias(self):
        show = self.make_show(playwright="Fred Bloggs", student_written=True)
        assert shows.get_crew_with_student_playwright(
            show, Path("_shows/00_01/a_show.md")
        ) == [models.PersonRef(role="Playwright", name="Fred Bloggs")]

    def test_playwright_false_suppresses_the_credit(self):
        show = self.make_show(
            playwright="Fred Bloggs", student_written=True, playwright_false=True
        )
        assert (
            shows.get_crew_with_student_playwright(show, Path("_shows/00_01/a_show.md"))
            == []
        )

    @pytest.mark.parametrize(
        "playwright",
        [
            "Fred Bloggs and Alice Froggs",
            "Fred Bloggs, Alice Froggs",
            "Fred Bloggs & Alice Froggs",
            "Fred Bloggs, and Alice Froggs",
        ],
    )
    def test_multiple_writers_get_a_credit_each(self, playwright: str):
        show = self.make_show(playwright=playwright, student_written=True)
        assert shows.get_crew_with_student_playwright(
            show, Path("_shows/00_01/a_show.md")
        ) == [
            models.PersonRef(role="Playwright", name="Fred Bloggs"),
            models.PersonRef(role="Playwright", name="Alice Froggs"),
        ]

    def test_alias_not_applied_to_multiple_writers(self):
        show = self.make_show(
            playwright="Fred Bloggs and Alice Froggs",
            playwright_alias="Freddie Bloggs",
            student_written=True,
        )
        assert shows.get_crew_with_student_playwright(
            show, Path("_shows/00_01/a_show.md")
        ) == [
            models.PersonRef(role="Playwright", name="Fred Bloggs"),
            models.PersonRef(role="Playwright", name="Alice Froggs"),
        ]

    def test_not_student_written_gets_no_credit(self):
        show = self.make_show(playwright="William Shakespeare")
        assert (
            shows.get_crew_with_student_playwright(show, Path("_shows/00_01/a_show.md"))
            == []
        )

    @pytest.mark.parametrize("playwright", ["various", "Unknown", "NNT Creatives"])
    def test_non_person_playwrights_get_no_credit(self, playwright: str):
        """content/_shows/20_21/speaking_solo.md and the like."""
        show = self.make_show(playwright=playwright, student_written=True)
        assert (
            shows.get_crew_with_student_playwright(show, Path("_shows/00_01/a_show.md"))
            == []
        )

    def test_hand_written_credit_left_alone(self, caplog: pytest.LogCaptureFixture):
        show = self.make_show(
            playwright="Fred Bloggs",
            student_written=True,
            crew=[models.PersonRef(role="Playwright", name="Fred Bloggs")],
        )
        assert (
            shows.get_crew_with_student_playwright(show, Path("_shows/00_01/a_show.md"))
            == show.crew
        )
        assert "by hand" in caplog.text


class TestShowTrivia:
    def test_a_show_without_trivia_has_none(self, test_db):
        make_show("show")
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert show_detail.trivia == []

    def test_trivia_targeted_at_the_show_is_embedded(self, test_db):
        make_show("show")
        database.Trivia.create(
            target_id="1999-00/show",
            target_type=database.TargetType.SHOW,
            target_name="A Show",
            target_image_id=None,
            target_year=1999,
            person_id="fred_bloggs",
            person_name="Fred Bloggs",
            quote="A quote",
            submitted="2001-06",
            data="{}",
        )
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert len(show_detail.trivia) == 1
        assert show_detail.trivia[0].quote == "A quote"
        assert show_detail.trivia[0].person is not None
        assert show_detail.trivia[0].person.id == "fred_bloggs"
        assert show_detail.trivia[0].person.title == "Fred Bloggs"

    def test_trivia_targeted_at_another_show_is_not_embedded(self, test_db):
        make_show("show")
        make_show("other")
        database.Trivia.create(
            target_id="1999-00/other",
            target_type=database.TargetType.SHOW,
            target_name="Other Show",
            target_image_id=None,
            target_year=1999,
            person_id=None,
            person_name=None,
            quote="A quote",
            submitted=None,
            data="{}",
        )
        show_detail = shows.get_show_detail(database.Show.get_by_id("1999-00/show"))
        assert show_detail.trivia == []


class TestShowDefects:
    @staticmethod
    def make_show(**kwargs) -> models.Show:
        return models.Show(
            **{"id": "a_show", "title": "A Show", "season": "In House", **kwargs}
        )

    def test_a_sound_show_has_no_defects(self):
        assert shows.get_show_defects(self.make_show(playwright="Fred Bloggs")) == []

    def test_devised_alongside_playwright(self):
        defects = shows.get_show_defects(
            self.make_show(playwright="Fred Bloggs", devised=True)
        )
        assert len(defects) == 1
        assert "devised" in defects[0]

    def test_improvised_alongside_playwright(self):
        defects = shows.get_show_defects(
            self.make_show(playwright="Fred Bloggs", improvised=True)
        )
        assert len(defects) == 1
        assert "improvised" in defects[0]

    def test_alias_on_several_writers_is_inert(self):
        defects = shows.get_show_defects(
            self.make_show(
                playwright="Fred Bloggs and Alice Froggs",
                playwright_alias="Freddie Bloggs",
                student_written=True,
            )
        )
        assert any("inert" in defect for defect in defects)

    def test_several_student_writers_are_no_defect(self):
        defects = shows.get_show_defects(
            self.make_show(
                playwright="Fred Bloggs and Alice Froggs", student_written=True
            )
        )
        assert defects == []

    def test_inert_playwright_alias(self):
        defects = shows.get_show_defects(
            self.make_show(playwright="Fred Bloggs", playwright_alias="Freddie Bloggs")
        )
        assert any("inert" in defect for defect in defects)

    def test_alias_that_takes_effect_is_no_defect(self):
        assert (
            shows.get_show_defects(
                self.make_show(
                    playwright="Fred Bloggs",
                    playwright_alias="Freddie Bloggs",
                    student_written=True,
                )
            )
            == []
        )


class TestGetCanonicalPlays:
    def test_without_canonical_indexes_the_show_as_itself(self):
        show = models.Show(
            id="dr_faustus", title="Dr Faustus", season="In House", playwright="Marlowe"
        )
        assert shows.get_canonical_plays(show, "Marlowe") == [("Dr Faustus", "Marlowe")]

    def test_canonical_title_overrides_show_title(self):
        show = models.Show(
            id="dr_faustus",
            title="Dr Faustus",
            season="In House",
            playwright="Marlowe",
            canonical=[{"title": "Doctor Faustus"}],
        )
        assert shows.get_canonical_plays(show, "Marlowe") == [
            ("Doctor Faustus", "Marlowe")
        ]

    def test_each_entry_yields_a_play_with_fallbacks(self):
        show = models.Show(
            id="double_bill",
            title="Double Bill",
            season="In House",
            playwright="A. Writer",
            canonical=[
                {"title": "First Play"},
                {"title": "Second Play", "playwright": "B. Writer"},
                {"playwright": "C. Writer"},
            ],
        )
        assert shows.get_canonical_plays(show, "A. Writer") == [
            ("First Play", "A. Writer"),
            ("Second Play", "B. Writer"),
            ("Double Bill", "C. Writer"),
        ]


class TestSplitWriters:
    @pytest.mark.parametrize(
        ("credit", "names"),
        [
            ("Fred Bloggs", ["Fred Bloggs"]),
            ("Fred Bloggs and Alice Froggs", ["Fred Bloggs", "Alice Froggs"]),
            ("Fred Bloggs & Alice Froggs", ["Fred Bloggs", "Alice Froggs"]),
            (
                "Jamie Drew, Sam Marshall, and Joe Hadley",
                ["Jamie Drew", "Sam Marshall", "Joe Hadley"],
            ),
            (
                "Howard Bird, Crispin Harris and Tim Killick",
                ["Howard Bird", "Crispin Harris", "Tim Killick"],
            ),
        ],
    )
    def test_splits_on_commas_and_conjunctions(self, credit, names):
        assert shows.split_writers(credit) == names


class TestStudentWrittenCanonicalPlays:
    def test_joint_student_credit_indexes_each_writer(self):
        show = models.Show(
            id="a_show",
            title="A Show",
            season="In House",
            playwright="Fred Bloggs and Alice Froggs",
            student_written=True,
        )
        assert shows.get_canonical_plays(show, "Fred Bloggs and Alice Froggs") == [
            ("A Show", "Fred Bloggs"),
            ("A Show", "Alice Froggs"),
        ]

    def test_joint_credit_left_whole_when_not_student_written(self):
        show = models.Show(
            id="iolanthe",
            title="Iolanthe",
            season="In House",
            playwright="Gilbert & Sullivan",
        )
        assert shows.get_canonical_plays(show, "Gilbert & Sullivan") == [
            ("Iolanthe", "Gilbert & Sullivan")
        ]
