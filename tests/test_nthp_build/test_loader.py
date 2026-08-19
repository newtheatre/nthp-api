import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from nthp_api.nthp_build import database, models
from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.loader import (
    DataLoaderFunc,
    DocumentLoaderFunc,
    Loader,
    load_history,
    load_venue,
    print_validation_error,
    run_data_loader,
    run_document_loader,
)


@pytest.fixture(autouse=True)
def _content_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "content_root", tmp_path)
    return tmp_path


@pytest.fixture()
def _bound_db(test_db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(database, "db", test_db)
    return test_db


def test_run_document_loader_skips_broken_frontmatter(
    tmp_path: Path, _bound_db, caplog: pytest.LogCaptureFixture
) -> None:
    venues_dir = tmp_path / "_venues"
    venues_dir.mkdir()
    (venues_dir / "broken.md").write_text("---\ntitle: [unclosed\n---\nContent.\n")
    (venues_dir / "good.md").write_text("---\ntitle: Good Venue\n---\nContent.\n")

    venue_loader = Loader(
        type=DocumentLoaderFunc,
        path=Path("_venues"),
        schema_type=models.Venue,
        func=load_venue,
    )

    with caplog.at_level(logging.ERROR):
        run_document_loader(venue_loader)

    assert database.Venue.select().count() == 1
    assert database.Venue.get().name == "Good Venue"
    assert any(
        "Failed to parse frontmatter YAML" in record.getMessage()
        and "broken.md" in record.getMessage()
        for record in caplog.records
    )


def test_run_document_loader_warns_on_missing_frontmatter(
    tmp_path: Path, _bound_db, caplog: pytest.LogCaptureFixture
) -> None:
    venues_dir = tmp_path / "_venues"
    venues_dir.mkdir()
    (venues_dir / "no_frontmatter.md").write_text("Just some content, no fences.\n")

    venue_loader = Loader(
        type=DocumentLoaderFunc,
        path=Path("_venues"),
        schema_type=models.Venue,
        func=load_venue,
    )

    with caplog.at_level(logging.WARNING):
        run_document_loader(venue_loader)

    assert any(
        "No frontmatter found in" in record.getMessage()
        and "no_frontmatter.md" in record.getMessage()
        for record in caplog.records
    )


def test_run_data_loader_invalid_yaml_does_not_raise(
    tmp_path: Path, _bound_db, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "history.yaml").write_text("title: [unclosed\n")

    history_loader = Loader(
        type=DataLoaderFunc,
        path=Path("history.yaml"),
        schema_type=models.HistoryRecordCollection,
        func=load_history,
    )

    with caplog.at_level(logging.ERROR):
        run_data_loader(history_loader)

    assert any(
        "Failed to parse YAML" in record.getMessage()
        and "history.yaml" in record.getMessage()
        for record in caplog.records
    )


def test_run_data_loader_validation_error_does_not_raise(
    tmp_path: Path, _bound_db, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "history.yaml").write_text(
        "- year: 2000\n  academic_year: not_a_valid_year\n  title: A title\n"
        "  description: A description\n"
    )

    history_loader = Loader(
        type=DataLoaderFunc,
        path=Path("history.yaml"),
        schema_type=models.HistoryRecordCollection,
        func=load_history,
    )

    with caplog.at_level(logging.ERROR):
        run_data_loader(history_loader)

    assert any(
        "Validation error in" in record.getMessage()
        and "history.yaml" in record.getMessage()
        for record in caplog.records
    )
    assert database.HistoryRecord.select().count() == 0


def test_print_validation_error_with_real_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    try:
        models.Venue()  # type: ignore[call-arg]
    except ValidationError as error:
        with caplog.at_level(logging.ERROR):
            print_validation_error(error, Path("some/path.md"))
    else:
        raise AssertionError("Expected a ValidationError")

    assert any(
        "Validation error in some/path.md" in record.getMessage()
        for record in caplog.records
    )
