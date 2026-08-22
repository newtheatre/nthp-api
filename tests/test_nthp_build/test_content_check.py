"""Checking one content file at a time, as `nthp validate` does."""

from pathlib import Path

import pytest

from nthp_api.nthp_build import content_check, content_schema, database, loader
from nthp_api.nthp_build.config import settings

GOOD_SHOW = """---
title: Macbeth
season: In House
date_start: 1973-11-20
date_end: 1973-11-24
venue: Nottingham New Theatre
---
About the show.
"""

SHOW_WITH_UNKNOWN_KEY = """---
title: Hamlet
season: In House
adapted: Fred Bloggs
---
"""

SHOW_WITH_DATES_BACK_TO_FRONT = """---
title: Bouncers
season: In House
date_start: 1973-11-24
date_end: 1973-11-20
---
"""

SHOW_OUTSIDE_ITS_YEAR = """---
title: Godot
season: In House
date_start: 1999-11-20
---
"""

GOOD_PERSON = """---
title: Fred Bloggs
graduated: 1975
---
A biography.
"""

PERSON_WITH_BAD_DATE = """---
title: Alice Froggs
submitted: 04/01/2017
---
"""

VENUE = """---
title: The Zoo
built: 1925
---
"""

COMMITTEE = """---
title: 1973-74
committee:
  - role: President
    name: Fred Bloggs
---
"""


@pytest.fixture()
def content_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "content_root", tmp_path)
    (tmp_path / "_data").mkdir()
    (tmp_path / "_data" / "roles.yaml").write_text("- role: Director\n")
    (tmp_path / "_data" / "link-types.yaml").write_text(
        "- type: default\n- type: facebook\n  href: https://facebook.com/{}\n"
    )
    (tmp_path / "_data" / "history.yaml").write_text("[]\n")
    shows = tmp_path / "_shows" / "73_74"
    shows.mkdir(parents=True)
    (shows / "macbeth.md").write_text(GOOD_SHOW)
    (shows / "hamlet.md").write_text(SHOW_WITH_UNKNOWN_KEY)
    (shows / "bouncers.md").write_text(SHOW_WITH_DATES_BACK_TO_FRONT)
    (shows / "godot.md").write_text(SHOW_OUTSIDE_ITS_YEAR)
    people = tmp_path / "_people"
    people.mkdir()
    (people / "fred_bloggs.md").write_text(GOOD_PERSON)
    (people / "alice_froggs.md").write_text(PERSON_WITH_BAD_DATE)
    venues = tmp_path / "_venues"
    venues.mkdir()
    (venues / "the-zoo.md").write_text(VENUE)
    committees = tmp_path / "_committees"
    committees.mkdir()
    (committees / "73_74.md").write_text(COMMITTEE)
    return tmp_path


def check(path: Path) -> content_check.FileResult:
    return content_check.check_file(path)


class TestResolveDocumentType:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("content/_shows/73_74/macbeth.md", content_schema.SHOW),
            ("content/_people/fred_bloggs.md", content_schema.PERSON),
            ("content/_venues/the-zoo.md", content_schema.VENUE),
            ("content/_committees/73_74.md", content_schema.COMMITTEE),
            ("content/_data/history.yaml", content_schema.HISTORY),
            ("content/_data/roles.yaml", content_schema.ROLES),
            ("content/_data/link-types.yaml", content_schema.LINK_TYPES),
        ],
    )
    def test_the_directory_decides(self, path: str, expected):
        assert content_check.resolve_document_type(Path(path)) is expected

    def test_a_file_the_api_does_not_read_is_unknown(self):
        assert content_check.resolve_document_type(Path("content/README.md")) is None

    def test_an_unread_data_file_is_unknown(self):
        assert (
            content_check.resolve_document_type(Path("content/_data/careers.yaml"))
            is None
        )


class TestCheckFile:
    def test_a_good_show_has_nothing_to_report(self, content_root: Path):
        assert check(content_root / "_shows/73_74/macbeth.md").ok

    def test_an_unknown_key_is_reported_with_the_key_it_meant(self, content_root: Path):
        result = check(content_root / "_shows/73_74/hamlet.md")
        assert not result.ok
        assert result.problems[0].location == "adapted"
        assert "did you mean `adaptor`" in result.problems[0].message

    def test_dates_the_wrong_way_round_are_reported(self, content_root: Path):
        result = check(content_root / "_shows/73_74/bouncers.md")
        assert "before date_start" in result.problems[0].message

    def test_a_date_outside_the_folders_year_is_reported(self, content_root: Path):
        result = check(content_root / "_shows/73_74/godot.md")
        assert "outside the academic year" in result.problems[0].message

    def test_a_show_outside_a_year_folder_is_reported(self, content_root: Path):
        stray = content_root / "_shows" / "macbeth.md"
        stray.write_text(GOOD_SHOW)
        result = check(stray)
        assert "not in an academic year folder" in result.problems[0].message

    def test_an_unparsable_date_is_reported(self, content_root: Path):
        result = check(content_root / "_people/alice_froggs.md")
        assert not result.ok
        assert any("submitted" in problem.location for problem in result.problems)

    def test_a_file_the_api_does_not_read_is_reported(self, tmp_path: Path):
        path = tmp_path / "notes.md"
        path.write_text("hello")
        result = check(path)
        assert result.document_type is None
        assert "not a content file" in result.problems[0].message

    def test_unparsable_yaml_is_reported(self, content_root: Path):
        path = content_root / "_venues" / "broken.md"
        path.write_text("---\ntitle: [unclosed\n---\n")
        assert not check(path).ok

    def test_a_duplicate_key_is_reported(self, content_root: Path):
        path = content_root / "_venues" / "twice.md"
        path.write_text("---\ntitle: The Zoo\ntitle: The Zoo Annex\n---\n")
        result = check(path)
        assert "duplicate key" in result.problems[0].message

    def test_a_data_file_is_checked_as_a_list(self, content_root: Path):
        assert check(content_root / "_data/roles.yaml").ok

    def test_a_bad_data_file_is_reported(self, content_root: Path):
        path = content_root / "_data" / "roles.yaml"
        path.write_text("- roll: Director\n")
        assert not check(path).ok


class TestLinkChecks:
    def test_a_templated_type_without_a_username_is_reported(
        self, content_root: Path, test_db
    ):
        database.db.init(":memory:")
        loader.run_data_loaders()
        path = content_root / "_people" / "linked.md"
        path.write_text(
            "---\ntitle: Linked Person\nlinks:\n  - type: facebook\n"
            "    href: https://facebook.com/someone\n---\n"
        )
        result = check(path)
        assert "no username" in result.problems[0].message


class TestExpandPaths:
    def test_a_directory_becomes_its_documents(self, content_root: Path):
        found = content_check.expand_paths([content_root / "_shows"])
        assert {path.name for path in found} == {
            "macbeth.md",
            "hamlet.md",
            "bouncers.md",
            "godot.md",
        }

    def test_a_directory_includes_the_data_files_the_api_reads(
        self, content_root: Path
    ):
        found = content_check.expand_paths([content_root])
        assert content_root / "_data" / "roles.yaml" in found

    def test_underscored_files_are_skipped(self, content_root: Path):
        (content_root / "_shows" / "73_74" / "_skeleton.md").write_text("---\n---\n")
        found = content_check.expand_paths([content_root / "_shows"])
        assert all(not path.name.startswith("_") for path in found)


class TestAgreesWithTheLoader:
    """
    The point of the command: what it accepts is what a build accepts.

    A document the loader refuses is a document lost from the API, so the two
    have to agree on which ones those are.
    """

    def test_the_loader_stores_exactly_the_documents_that_validate(
        self, content_root: Path, test_db
    ):
        database.db.init(":memory:")
        loader.run_loaders()
        stored = {show.source_path for show in database.Show.select()}
        validating = {
            str(result.path.relative_to(content_root))
            for result in content_check.check_files([content_root / "_shows"])
            if not any(problem.location != "document" for problem in result.problems)
        }
        assert stored == validating

    def test_a_defect_does_not_cost_the_document(self, content_root: Path, test_db):
        """A show with impossible dates is still loaded, and still reported."""
        database.db.init(":memory:")
        loader.run_loaders()
        assert (
            database.Show.select()
            .where(database.Show.source_path == "_shows/73_74/bouncers.md")
            .exists()
        )
        assert not check(content_root / "_shows/73_74/bouncers.md").ok
