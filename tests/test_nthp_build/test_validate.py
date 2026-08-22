import logging

import pytest

from nthp_api.nthp_build import database, models, validate


def make_show(
    show_id: str = "1999-00/a_show",
    title: str = "A Show",
    venue: str | None = None,
    venue_id: str | None = None,
    season_id: str | None = "in-house",
    **data,
) -> database.Show:
    return database.Show.create(
        id=show_id,
        source_path=f"_shows/{show_id}.md",
        year=1999,
        year_id="1999-00",
        title=title,
        venue_id=venue_id,
        venue_name=venue,
        venue_sort=data.get("venue_sort"),
        season_id=season_id,
        assets="[]",
        data=models.Show(
            id=show_id, title=title, season="In House", venue=venue, **data
        ).model_dump_json(),
    )


def make_person(person_id: str = "fred_bloggs", **data) -> database.Person:
    model = models.Person(**{"id": person_id, "title": "Fred Bloggs", **data})
    return database.Person.create(
        id=person_id,
        source_path=f"_people/{person_id}.md",
        title=model.title,
        graduated=model.graduated,
        data=model.model_dump_json(),
    )


PERSON_ROLE_DEFAULTS = {
    "target_id": "1999-00/a_show",
    "target_type": database.PersonRoleType.CREW,
    "target_year": 1999,
    "person_id": "fred_bloggs",
    "person_name": "Fred Bloggs",
    "role": "Director",
    "is_person": True,
    "data": "{}",
}


def make_role(**fields) -> database.PersonRole:
    return database.PersonRole.create(**{**PERSON_ROLE_DEFAULTS, **fields})


class TestVenueSpellings:
    def test_one_spelling_is_fine(self, test_db):
        make_show("1999-00/one", venue="The Zoo", venue_id="the-zoo")
        make_show("1999-00/two", venue="The Zoo", venue_id="the-zoo")
        assert validate.check_venue_spellings() == []

    def test_divergent_spellings_name_the_shows(self, test_db):
        make_show("1999-00/one", venue="The Zoo", venue_id="the-zoo")
        make_show("1999-00/two", venue="The zoo", venue_id="the-zoo")
        findings = validate.check_venue_spellings()
        assert len(findings) == 1
        assert findings[0].value == "the-zoo"
        assert "'The Zoo'" in findings[0].hint
        assert "'The zoo'" in findings[0].hint
        assert "_shows/1999-00/one.md" in findings[0].hint


class TestAwardGraduation:
    def test_award_with_a_graduation_year_is_fine(self, test_db):
        make_person(award="Fellowship", graduated=2000)
        assert validate.check_award_graduation() == []

    def test_award_without_a_graduation_year(self, test_db):
        make_person(award="Fellowship")
        findings = validate.check_award_graduation()
        assert len(findings) == 1
        assert findings[0].source_path == "_people/fred_bloggs.md"

    def test_no_award_is_fine(self, test_db):
        make_person()
        assert validate.check_award_graduation() == []


class TestDuplicateIds:
    @staticmethod
    def make_playwright_show(
        play_name: str, playwright_name: str, show_id: str
    ) -> None:
        from nthp_api.nthp_build import playwrights

        playwrights.save_playwright_show(
            play_name=play_name,
            playwright_name=playwright_name,
            show_id=show_id,
            student_written=False,
        )

    def test_one_spelling_is_fine(self, test_db):
        self.make_playwright_show("Mojo", "Jez Butterworth", "2013-14/mojo")
        self.make_playwright_show("Mojo", "Jez Butterworth", "2021-22/mojo")
        assert validate.check_play_ids() == []
        assert validate.check_playwright_ids() == []

    def test_two_play_names_behind_one_id(self, test_db):
        self.make_playwright_show("MOJO", "Jez Butterworth", "2013-14/mojo")
        self.make_playwright_show("Mojo", "Jez Butterworth", "2021-22/mojo")
        findings = validate.check_play_ids()
        assert len(findings) == 1
        assert findings[0].value == "mojo"

    def test_two_playwright_names_behind_one_id(self, test_db):
        self.make_playwright_show("Blood Wedding", "Federico Garcia Lorca", "a")
        self.make_playwright_show("Yerma", "Federico García Lorca", "b")
        findings = validate.check_playwright_ids()
        assert len(findings) == 1
        assert findings[0].value == "federico_garcia_lorca"


class TestPersonNameCollisions:
    def test_one_name_is_fine(self, test_db):
        make_role()
        make_role(target_id="1999-00/other")
        assert validate.check_person_name_collisions() == []

    def test_two_names_without_a_document(self, test_db):
        make_role(person_name="Fred Bloggs")
        make_role(person_name="Freddie Bloggs", target_id="1999-00/other")
        findings = validate.check_person_name_collisions()
        assert len(findings) == 1
        assert findings[0].value == "fred_bloggs"
        assert "Freddie Bloggs" in findings[0].hint

    def test_two_names_with_a_document_are_settled(self, test_db):
        make_person()
        make_role(person_name="Fred Bloggs")
        make_role(person_name="Freddie Bloggs", target_id="1999-00/other")
        assert validate.check_person_name_collisions() == []


class TestCommitteeRoles:
    def test_a_named_role_is_fine(self, test_db):
        make_role(target_type=database.PersonRoleType.COMMITTEE, role="Chair")
        assert validate.check_committee_roles() == []

    @pytest.mark.parametrize("role", [None, "unknown", "Unknown"])
    def test_an_unknown_role(self, test_db, role: str | None):
        make_role(target_type=database.PersonRoleType.COMMITTEE, role=role)
        assert len(validate.check_committee_roles()) == 1


class TestTriviaPeople:
    @staticmethod
    def make_trivia(person_id: str) -> None:
        database.Trivia.create(
            target_id="1999-00/a_show",
            target_type=database.TargetType.SHOW,
            target_name="A Show",
            target_year=1999,
            person_id=person_id,
            person_name="Fred Bloggs",
            quote="A fact.",
            data="{}",
        )

    def test_a_credited_person_is_fine(self, test_db):
        make_role()
        self.make_trivia("fred_bloggs")
        assert validate.check_trivia_people() == []

    def test_a_documented_person_is_fine(self, test_db):
        make_person()
        self.make_trivia("fred_bloggs")
        assert validate.check_trivia_people() == []

    def test_an_unknown_person(self, test_db):
        self.make_trivia("fred_bloggs")
        assert len(validate.check_trivia_people()) == 1


class TestAwardsKnown:
    def test_a_known_award(self, test_db):
        make_person(award="Fellowship", graduated=2000)
        assert validate.check_awards_known() == []

    def test_an_unknown_award(self, test_db):
        make_person(award="Knighthood", graduated=2000)
        assert len(validate.check_awards_known()) == 1


class TestGraduationPlausibility:
    def test_a_plausible_graduation(self, test_db):
        make_person(graduated=2000)
        make_role(target_year=1999)
        assert validate.check_graduation_plausible() == []

    def test_graduated_before_the_first_credit(self, test_db):
        make_person(graduated=1990)
        make_role(target_year=1999)
        findings = validate.check_graduation_plausible()
        assert len(findings) == 1
        assert "before their first credit" in findings[0].hint

    def test_graduated_long_after_the_last_credit(self, test_db):
        make_person(graduated=2020)
        make_role(target_year=1999)
        findings = validate.check_graduation_plausible()
        assert len(findings) == 1
        assert "after their last credit" in findings[0].hint

    def test_without_credits_there_is_nothing_to_compare(self, test_db):
        make_person(graduated=1990)
        assert validate.check_graduation_plausible() == []


class TestTourDates:
    def test_a_tour_date_with_a_venue(self, test_db):
        make_show(tour=[models.TourDate(venue="The Zoo")])
        assert validate.check_tour_dates() == []

    def test_a_tour_date_with_neither_venue_nor_date(self, test_db):
        make_show(tour=[models.TourDate(note="A note")])
        findings = validate.check_tour_dates()
        assert len(findings) == 1
        assert findings[0].source_path == "_shows/1999-00/a_show.md"


class TestCreditsWithoutAName:
    def test_a_named_credit(self, test_db):
        make_role()
        assert validate.check_person_refs_named() == []

    def test_a_credit_without_a_name(self, test_db):
        make_role(person_id=None, person_name=None)
        assert len(validate.check_person_refs_named()) == 1


class TestImageCategories:
    @staticmethod
    def make_image(category: str) -> None:
        from nthp_api.nthp_build import assets

        assets.save_asset(
            "1999-00/a_show",
            assets.AssetTarget.SHOW,
            assets.AssetSource.SMUGMUG,
            assets.AssetType.IMAGE,
            "abc123",
            category=category,
        )

    def test_a_known_category(self, test_db):
        self.make_image("poster")
        assert validate.check_asset_categories() == []

    def test_an_unknown_category(self, test_db):
        self.make_image("banner")
        findings = validate.check_asset_categories()
        assert len(findings) == 1
        assert findings[0].value == "banner"


class TestVenueSort:
    def test_venue_sort_with_a_venue(self, test_db):
        make_show(venue="The Zoo", venue_id="the-zoo", venue_sort="Fringe")
        assert validate.check_venue_sort() == []

    def test_venue_sort_without_a_venue(self, test_db):
        make_show(venue_sort="Fringe")
        assert len(validate.check_venue_sort()) == 1


class TestNearDuplicatePersonIds:
    def test_distinct_people(self, test_db):
        make_person("fred_bloggs")
        make_person("alice_froggs")
        assert validate.check_near_duplicate_person_ids() == []

    def test_forenames_that_only_share_a_first_letter(self, test_db):
        make_person("caroline_jones")
        make_person("clare_jones")
        assert validate.check_near_duplicate_person_ids() == []

    def test_a_short_form_of_a_forename(self, test_db):
        make_person("joe_bloggs")
        make_person("joseph_bloggs")
        findings = validate.check_near_duplicate_person_ids()
        assert len(findings) == 1
        assert findings[0].value == "joe_bloggs / joseph_bloggs"


class TestShowSeasons:
    def test_a_recognised_season(self, test_db):
        make_show()
        assert validate.check_show_seasons() == []

    def test_an_unrecognised_season(self, test_db):
        make_show(season_id=None)
        assert len(validate.check_show_seasons()) == 1


class TestVenueDocuments:
    def test_a_documented_venue(self, test_db):
        database.Venue.create(id="the-zoo", name="The Zoo", data="{}")
        make_show(venue="The Zoo", venue_id="the-zoo")
        assert validate.check_venue_documents() == []

    def test_a_venue_without_a_document(self, test_db):
        make_show(venue="The Zoo", venue_id="the-zoo")
        findings = validate.check_venue_documents()
        assert len(findings) == 1
        assert findings[0].value == "the-zoo"

    def test_a_sentinel_venue_needs_no_document(self, test_db):
        make_show(venue="Unknown", venue_id="unknown")
        assert validate.check_venue_documents() == []


class TestRecordedFindings:
    def test_placeholder_content_is_recorded(self, test_db):
        validate.check_content_is_not_a_placeholder(
            "\n<!-- Nothing here yet -->\n", "_people/fred_bloggs.md"
        )
        findings = validate.check_placeholder_content()
        assert len(findings) == 1
        assert findings[0].source_path == "_people/fred_bloggs.md"

    def test_real_content_is_not_recorded(self, test_db):
        validate.check_content_is_not_a_placeholder(
            "<!-- a note -->\nA biography.\n", "_people/fred_bloggs.md"
        )
        assert validate.check_placeholder_content() == []

    def test_empty_content_is_not_recorded(self, test_db):
        validate.check_content_is_not_a_placeholder("  \n", "_people/fred_bloggs.md")
        assert validate.check_placeholder_content() == []


class TestRunBuildChecks:
    def test_defects_are_logged_as_errors(
        self, test_db, caplog: pytest.LogCaptureFixture
    ):
        make_person(award="Fellowship")
        with caplog.at_level(logging.ERROR):
            assert validate.run_build_checks() == 1
        assert "award-graduation" in caplog.text
        assert caplog.records[0].levelname == "ERROR"

    def test_a_clean_build_reports_nothing(
        self, test_db, caplog: pytest.LogCaptureFixture
    ):
        make_show()
        with caplog.at_level(logging.ERROR):
            assert validate.run_build_checks() == 0
        assert not caplog.records


class TestLintChecks:
    def test_every_check_runs(self, test_db):
        results = validate.run_lint_checks()
        assert len(results) == len(validate.LINT_CHECKS)
        assert all(findings == [] for findings in results.values())

    def test_a_named_check_runs_alone(self, test_db):
        make_show(season_id=None)
        results = validate.run_lint_checks(["show-seasons"])
        assert [check.name for check in results] == ["show-seasons"]
        assert len(results[validate.CHECKS_BY_NAME["show-seasons"]]) == 1
