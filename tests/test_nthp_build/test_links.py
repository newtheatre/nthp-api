from pathlib import Path

import pytest

from nthp_api.nthp_build import database, links, models
from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.loader import (
    DataLoaderFunc,
    Loader,
    load_link_type_definitions,
    run_data_loader,
)

LINK_TYPES_YAML = """
- type: default
  icon: fa fa-link

- type: Personal Website

- type: Twitter
  icon: fa fa-twitter
  href: https://twitter.com/???

- type: Review
  icon: fa fa-newspaper-o
  is_news: true

- type: Recording\x20
  icon: fa fa-video-camera\x20
"""


@pytest.fixture()
def _bound_db(test_db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(database, "db", test_db)
    return test_db


@pytest.fixture()
def _link_type_definitions(
    test_db, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _bound_db
) -> None:
    monkeypatch.setattr(settings, "content_root", tmp_path)
    data_dir = tmp_path / "_data"
    data_dir.mkdir()
    (data_dir / "link-types.yaml").write_text(LINK_TYPES_YAML)
    run_data_loader(
        Loader(
            type=DataLoaderFunc,
            path=Path("_data/link-types.yaml"),
            schema_type=models.LinkTypeDefinitionCollection,
            func=load_link_type_definitions,
        )
    )


class TestLinkTypeDefinitions:
    @pytest.mark.usefixtures("_link_type_definitions")
    def test_loads_definitions(self):
        definitions = links.get_link_type_definitions()
        assert definitions["twitter"].href == "https://twitter.com/???"
        assert definitions["review"].is_news is True
        assert definitions["personal website"].is_news is False

    @pytest.mark.usefixtures("_link_type_definitions")
    def test_strips_trailing_whitespace(self):
        assert links.get_link_type_definitions()["recording"].type == "Recording"


@pytest.mark.usefixtures("_link_type_definitions")
class TestGetLink:
    def test_resolves_templated_href_from_username(self):
        link = links.get_link(models.Link(type="Twitter", username="nnt_official"))
        assert link.href == "https://twitter.com/nnt_official"
        assert link.username == "nnt_official"

    def test_templated_type_without_username_falls_back_to_href(
        self, caplog: pytest.LogCaptureFixture
    ):
        link = links.get_link(
            models.Link(type="Twitter", href="https://twitter.com/nnt_official")
        )
        assert link.href == "https://twitter.com/nnt_official"
        assert "no username" in caplog.text

    def test_keeps_authored_href(self):
        link = links.get_link(
            models.Link(type="Personal Website", href="https://example.com")
        )
        assert link.href == "https://example.com"

    def test_generates_snapshot_href(self):
        link = links.get_link(
            models.Link(
                type="Review", href="https://example.com/review", snapshot="abc12"
            )
        )
        assert link.href_snapshot == "https://archive.is/abc12"

    def test_no_snapshot_no_snapshot_href(self):
        link = links.get_link(models.Link(type="Review", href="https://example.com"))
        assert link.href_snapshot is None

    def test_canonicalises_type_name(self):
        assert links.get_link(models.Link(type="review")).type == "Review"

    def test_undefined_type_keeps_authored_name(self):
        link = links.get_link(models.Link(type="Muck Rack", href="https://example.com"))
        assert link.type == "Muck Rack"
        assert link.is_news is False

    def test_news_type_flagged(self):
        assert links.get_link(models.Link(type="Review")).is_news is True

    def test_carries_review_fields(self):
        link = links.get_link(
            models.Link(
                type="Review",
                href="https://example.com/review",
                title="Student theatre at its best",
                date="2022-01-31",
                publisher="Impact Magazine",
                rating="4/5",
                quote="A triumph",
                note="Subscription required",
            )
        )
        assert link.title == "Student theatre at its best"
        assert str(link.date) == "2022-01-31"
        assert link.publisher == "Impact Magazine"
        assert link.rating == "4/5"
        assert link.quote == "A triumph"
        assert link.note == "Subscription required"

    def test_get_links(self):
        assert (
            len(
                links.get_links(
                    [models.Link(type="Review"), models.Link(type="Twitter", username="x")]
                )
            )
            == 2  # noqa: PLR2004
        )
