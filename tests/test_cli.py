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
    def test_lint_reports_every_check(self, content_root: Path):
        result = run_lint(content_root)
        assert result.exit_code == 0
        assert "venues without a document" in result.output
        assert "total" in result.output

    def test_lint_reports_the_content_findings(self, content_root: Path):
        result = run_lint(content_root)
        assert "_people/freddie_bloggs.md: course is a bare value" in result.output
        assert "body is only an HTML comment" in result.output
        assert "venue 'the-zoo' has no document (1 shows)" in result.output
        assert "outside the known set" in result.output

    def test_lint_never_fails(self, content_root: Path):
        assert run_lint(content_root).exit_code == 0

    def test_examples_option_limits_the_listing(self, content_root: Path):
        result = run_lint(content_root, "--examples", "0")
        assert "course is a bare value" not in result.output
        assert "... and 1 more" in result.output
