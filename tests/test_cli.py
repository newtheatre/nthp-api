"""The CLI commands, driven as a user drives them."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from nthp_api.cli import cli
from nthp_api.nthp_build import content_schema

SHOW = """---
title: A Show
season: In House
venue: The Zoo
crew:
  - role: Director
    name: Fred Bloggs
  - role: Bagpiper
    name: Alice Froggs
---
About the show.
"""

PERSON = """---
title: Freddie Bloggs
course: Drama
award: Knighthood
---
<!-- Nothing here yet -->
"""


@pytest.fixture()
def content_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A miniature content repo, with the CLI pointed at an in-memory database."""
    from nthp_api.nthp_build import database
    from nthp_api.nthp_build.config import settings

    monkeypatch.setattr(settings, "content_root", tmp_path)
    monkeypatch.setattr(settings, "db_uri", ":memory:")
    database.db.init(":memory:")

    (tmp_path / "_data").mkdir()
    (tmp_path / "_data" / "roles.yaml").write_text("- role: Director\n")
    (tmp_path / "_data" / "link-types.yaml").write_text("- type: default\n")
    (tmp_path / "_data" / "history.yaml").write_text("[]\n")
    shows_dir = tmp_path / "_shows" / "99_00"
    shows_dir.mkdir(parents=True)
    (shows_dir / "a_show.md").write_text(SHOW)
    people_dir = tmp_path / "_people"
    people_dir.mkdir()
    (people_dir / "freddie_bloggs.md").write_text(PERSON)
    return tmp_path


def run_lint(content_root: Path, *args: str):
    return CliRunner().invoke(cli, ["lint", str(content_root), *args])


class TestLint:
    def test_every_check_gets_a_heading_and_an_explanation(self, content_root: Path):
        result = run_lint(content_root)
        assert result.exit_code == 0
        assert "Venues with no document (1)  [venue-documents]" in result.output
        assert "dumped as stubs" in result.output

    def test_findings_name_the_document_and_the_value(self, content_root: Path):
        result = run_lint(content_root)
        assert "_people/freddie_bloggs.md" in result.output
        assert "course" in result.output
        assert "the-zoo" in result.output

    def test_a_check_with_nothing_to_report_says_so(self, content_root: Path):
        assert "Nothing to report." in run_lint(content_root).output

    def test_summary_table_counts_every_check(self, content_root: Path):
        result = run_lint(content_root)
        assert "Summary" in result.output
        assert "total" in result.output
        assert "advisory" in result.output
        assert "worth fixing" in result.output

    def test_lint_never_fails(self, content_root: Path):
        assert run_lint(content_root).exit_code == 0

    def test_check_option_runs_one_check(self, content_root: Path):
        result = run_lint(content_root, "--check", "venue-documents")
        assert "[venue-documents]" in result.output
        assert "[crew-roles]" not in result.output

    def test_an_unknown_check_is_rejected(self, content_root: Path):
        result = run_lint(content_root, "--check", "nonsense")
        assert result.exit_code != 0
        assert "unknown check" in result.output

    def test_plain_format_has_no_colour(self, content_root: Path):
        result = run_lint(content_root, "--format", "plain")
        assert "\x1b[" not in result.output

    def test_verbose_lists_every_finding(self, content_root: Path):
        result = run_lint(content_root, "--check", "crew-roles", "--verbose")
        assert "more, run with --verbose" not in result.output


def run_schema(*args: str):
    return CliRunner().invoke(cli, ["schema", *args])


class TestSchema:
    def test_a_type_prints_its_json_schema(self):
        result = run_schema("show")
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert schema["$id"] == "show.json"
        assert schema["additionalProperties"] is False

    def test_no_type_prints_every_schema(self):
        result = run_schema()
        assert set(json.loads(result.output)) == {
            document_type.name
            for document_type in content_schema.CONTENT_DOCUMENT_TYPES
        }

    def test_markdown_is_for_reading(self):
        result = run_schema("person", "--format", "markdown")
        assert "# Person" in result.output
        assert "| Field | Type | Required | Description | Example |" in result.output

    def test_an_unknown_type_is_rejected(self):
        result = run_schema("nonsense")
        assert result.exit_code != 0
        assert "unknown type" in result.output


def run_validate(*args: str):
    return CliRunner().invoke(cli, ["validate", *args])


class TestValidate:
    def test_a_good_file_passes(self, content_root: Path):
        result = run_validate(str(content_root / "_shows" / "99_00" / "a_show.md"))
        assert result.exit_code == 0
        assert "0 with problems" in result.output

    def test_a_bad_file_fails_and_names_the_key(self, content_root: Path):
        path = content_root / "_shows" / "99_00" / "broken.md"
        path.write_text(
            "---\ntitle: Broken\nseason: In House\nplayright: A N Other\n---\n"
        )
        result = run_validate(str(path))
        assert result.exit_code == 1
        assert "playright" in result.output
        assert "1 with problems" in result.output

    def test_a_directory_checks_everything_under_it(self, content_root: Path):
        result = run_validate(str(content_root))
        assert "files checked" in result.output

    def test_verbose_names_the_files_with_nothing_wrong(self, content_root: Path):
        result = run_validate(str(content_root / "_shows"), "--verbose")
        assert "no problems" in result.output

    def test_plain_format_has_no_colour(self, content_root: Path):
        result = run_validate(str(content_root), "--format", "plain")
        assert "\x1b[" not in result.output


def run_new(*args: str):
    return CliRunner().invoke(cli, ["new", *args])


class TestNew:
    def test_a_skeleton_is_front_matter(self):
        result = run_new("show")
        assert result.exit_code == 0
        assert result.output.startswith("---\n")

    def test_an_identifier_names_the_file(self):
        result = run_new("person", "--id", "fred_bloggs")
        assert "_people/fred_bloggs.md" in result.output
        assert "title: Fred Bloggs" in result.output

    def test_an_unknown_type_is_rejected(self):
        assert run_new("committee").exit_code != 0
