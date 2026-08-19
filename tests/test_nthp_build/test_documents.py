import logging
from pathlib import Path

import pytest
import yaml

from nthp_api.nthp_build import documents
from nthp_api.nthp_build.config import settings


@pytest.fixture(autouse=True)
def _content_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "content_root", tmp_path)
    return tmp_path


def test_load_document_logs_duplicate_frontmatter_key(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "show.md"
    path.write_text(
        "---\ntitle: First\nplaywright: Someone\ntitle: Second\n---\nContent.\n"
    )

    with caplog.at_level(logging.WARNING):
        post = documents.load_document(path)

    assert post.metadata["title"] == "Second"
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.ERROR
    message = caplog.records[0].getMessage()
    assert "Duplicate key 'title'" in message
    assert "in show.md" in message
    assert "lines 2 and 4" in message


def test_load_document_without_duplicates_logs_nothing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "show.md"
    path.write_text("---\ntitle: A Show\nplaywright: Someone\n---\nContent.\n")

    with caplog.at_level(logging.WARNING):
        documents.load_document(path)

    assert caplog.records == []


def test_load_yaml_logs_duplicate_key(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "history.yaml").write_text(
        "title: First\nplaywright: Someone\ntitle: Second\n"
    )

    with caplog.at_level(logging.WARNING):
        data = documents.load_yaml("history.yaml")

    assert data["title"] == "Second"
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.ERROR
    message = caplog.records[0].getMessage()
    assert "Duplicate key 'title'" in message
    assert "lines 1 and 3" in message


def test_load_yaml_invalid_yaml_raises(tmp_path: Path) -> None:
    (tmp_path / "history.yaml").write_text("title: [unclosed\n")

    with pytest.raises(yaml.YAMLError):
        documents.load_yaml("history.yaml")
