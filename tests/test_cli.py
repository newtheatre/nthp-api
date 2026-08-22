"""The CLI commands, driven as a user drives them."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from nthp_api.cli import cli

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
