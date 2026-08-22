import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from nthp_api.nthp_build import database, history, models, schema
from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.loader import (
    DataLoaderFunc,
    DocumentLoaderFunc,
    Loader,
    load_history,
    load_show,
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


def test_run_document_loader_logs_error_when_show_ends_before_it_starts(
    tmp_path: Path, _bound_db, caplog: pytest.LogCaptureFixture
) -> None:
    shows_dir = tmp_path / "_shows" / "06_07"
    shows_dir.mkdir(parents=True)
    (shows_dir / "house_of_bernada_alba.md").write_text(
        "---\n"
        "title: The House of Bernada Alba\n"
        "season: Spring\n"
        "date_start: 2007-03-20\n"
        "date_end: 2007-03-13\n"
        "---\n"
        "Content.\n"
    )

    show_loader = Loader(
        type=DocumentLoaderFunc,
        path=Path("_shows"),
        schema_type=models.Show,
        func=load_show,
    )

    with caplog.at_level(logging.ERROR):
        run_document_loader(show_loader)

    assert database.Show.select().count() == 1
    assert any(
        "_shows/06_07/house_of_bernada_alba.md" in record.getMessage()
        and "date_end" in record.getMessage()
        and "before" in record.getMessage()
        for record in caplog.records
    )


def test_load_show_does_not_log_when_dates_are_fuzzy_but_not_conflicting(
    tmp_path: Path, _bound_db, caplog: pytest.LogCaptureFixture
) -> None:
    shows_dir = tmp_path / "_shows" / "06_07"
    shows_dir.mkdir(parents=True)
    (shows_dir / "some_show.md").write_text(
        "---\n"
        "title: Some Show\n"
        "season: Spring\n"
        "date_start: 2006-03\n"
        "date_end: 2006\n"
        "---\n"
        "Content.\n"
    )

    show_loader = Loader(
        type=DocumentLoaderFunc,
        path=Path("_shows"),
        schema_type=models.Show,
        func=load_show,
    )

    with caplog.at_level(logging.ERROR):
        run_document_loader(show_loader)

    assert not any(
        "before" in record.getMessage() and "date_end" in record.getMessage()
        for record in caplog.records
    )


def test_history_record_image_loaded_and_output(tmp_path: Path, _bound_db) -> None:
    (tmp_path / "history.yaml").write_text(
        "- year: 1927\n  title: Formation of Dramsoc\n  description: A description\n"
        "  image:\n    href: https://example.com/image.jpg\n    alt: Old auditorium\n"
        "- year: 1940\n  title: Formation of TEC\n  description: Another description\n"
    )

    run_data_loader(
        Loader(
            type=DataLoaderFunc,
            path=Path("history.yaml"),
            schema_type=models.HistoryRecordCollection,
            func=load_history,
        )
    )

    records = history.get_history_records()
    assert records[0].image == schema.HistoryRecordImage(
        href="https://example.com/image.jpg", alt="Old auditorium"
    )
    assert records[1].image is None


def test_run_document_loader_logs_error_when_date_is_outside_the_folder_year(
    tmp_path: Path, _bound_db, caplog: pytest.LogCaptureFixture
) -> None:
    shows_dir = tmp_path / "_shows" / "06_07"
    shows_dir.mkdir(parents=True)
    (shows_dir / "a_show.md").write_text(
        "---\ntitle: A Show\nseason: Spring\ndate_start: 2009-03-20\n---\nContent.\n"
    )

    with caplog.at_level(logging.ERROR):
        run_document_loader(
            Loader(
                type=DocumentLoaderFunc,
                path=Path("_shows"),
                schema_type=models.Show,
                func=load_show,
            )
        )

    assert database.Show.select().count() == 1
    assert any(
        "_shows/06_07/a_show.md" in record.getMessage()
        and "outside the academic year 2006-07" in record.getMessage()
        for record in caplog.records
    )


def test_run_document_loader_logs_show_defects(
    tmp_path: Path, _bound_db, caplog: pytest.LogCaptureFixture
) -> None:
    shows_dir = tmp_path / "_shows" / "06_07"
    shows_dir.mkdir(parents=True)
    (shows_dir / "a_show.md").write_text(
        "---\n"
        "title: A Show\n"
        "season: Spring\n"
        "playwright: Fred Bloggs\n"
        "devised: true\n"
        "---\n"
        "Content.\n"
    )

    with caplog.at_level(logging.ERROR):
        run_document_loader(
            Loader(
                type=DocumentLoaderFunc,
                path=Path("_shows"),
                schema_type=models.Show,
                func=load_show,
            )
        )

    assert any(
        "_shows/06_07/a_show.md" in record.getMessage()
        and "is dropped" in record.getMessage()
        for record in caplog.records
    )


def test_data_loaders_run_before_documents() -> None:
    """Document checks consult the `_data` definitions, so those load first."""
    from nthp_api.nthp_build.loader import LOADERS

    data_loader_indexes = [
        index for index, loader in enumerate(LOADERS) if loader.type is DataLoaderFunc
    ]
    document_loader_indexes = [
        index
        for index, loader in enumerate(LOADERS)
        if loader.type is DocumentLoaderFunc
    ]
    assert max(data_loader_indexes) < min(document_loader_indexes)
