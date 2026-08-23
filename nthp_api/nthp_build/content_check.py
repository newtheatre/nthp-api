"""
Validating one content file at a time, as an editor or an agent writes it.

`nthp load` reports a whole repository; this reports a single file, against the
same models and the same per-document checks, so a file this accepts is a file
the build accepts. Anything needing the whole repository to see — two spellings
of a venue, a name credited two ways — belongs to `nthp lint` instead.
"""

import logging
from pathlib import Path
from typing import Any, NamedTuple

import frontmatter
import yaml
from pydantic import BaseModel, ValidationError
from pydantic_collections import BaseCollectionModel
from pydantic_core import ErrorDetails

from nthp_api.nthp_build import links, shows, validation_messages, years
from nthp_api.nthp_build.content_schema import (
    COMMITTEE,
    HISTORY,
    LINK_TYPES,
    PERSON,
    ROLES,
    SHOW,
    VENUE,
    ContentDocumentType,
)
from nthp_api.nthp_build.documents import DuplicateKeyDetectingYAMLHandler
from nthp_api.nthp_build.yaml_loader import load_yaml_detecting_duplicates

log = logging.getLogger(__name__)

DOCUMENT_DIRECTORIES: dict[str, ContentDocumentType] = {
    "_shows": SHOW,
    "_people": PERSON,
    "_venues": VENUE,
    "_committees": COMMITTEE,
}

DATA_DIRECTORY = "_data"
DATA_FILES: dict[str, ContentDocumentType] = {
    "history.yaml": HISTORY,
    "roles.yaml": ROLES,
    "link-types.yaml": LINK_TYPES,
}


class Problem(NamedTuple):
    """One thing wrong with a file, and where in it."""

    location: str
    message: str
    value: str | None = None


class FileResult(NamedTuple):
    path: Path
    document_type: ContentDocumentType | None
    problems: list[Problem]

    @property
    def ok(self) -> bool:
        return not self.problems


def resolve_document_type(path: Path) -> ContentDocumentType | None:
    """Which kind of content file this is, from where it sits in the repository."""
    if path.parent.name == DATA_DIRECTORY:
        return DATA_FILES.get(path.name)
    for part in path.parts:
        if part in DOCUMENT_DIRECTORIES:
            return DOCUMENT_DIRECTORIES[part]
    return None


def expand_paths(paths: list[Path]) -> list[Path]:
    """Every content file under the paths given, directories expanded."""
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(
                sorted(
                    candidate
                    for candidate in path.rglob("*.md")
                    if not candidate.name.startswith("_")
                )
            )
            found.extend(
                sorted(
                    candidate
                    for candidate in path.rglob("*.yaml")
                    if resolve_document_type(candidate) is not None
                )
            )
        else:
            found.append(path)
    return found


def make_validation_problem(item: ErrorDetails, model: type[BaseModel]) -> Problem:
    """
    One pydantic error, worded as the loader words it.

    `describe_error` leads with the location, which has a column of its own here,
    so it is taken back off the front.
    """
    location = validation_messages.describe_location(item["loc"])
    described = validation_messages.describe_error(item, model)
    return Problem(
        location=location,
        message=described.removeprefix(f"{location}: "),
        value=repr(item.get("input")),
    )


def make_validation_problems(
    error: ValidationError, document_type: ContentDocumentType
) -> list[Problem]:
    return [
        make_validation_problem(item, document_type.record_model)
        for item in error.errors()
    ]


def get_duplicate_key_problems(duplicate_keys: list) -> list[Problem]:
    return [
        Problem(
            location=duplicate_key.key,
            message=(
                f"duplicate key, on lines {duplicate_key.first_line} and "
                f"{duplicate_key.duplicate_line}; the first value is discarded"
            ),
        )
        for duplicate_key in duplicate_keys
    ]


def get_show_rule_problems(path: Path, data: Any) -> list[Problem]:
    """The show checks the loader runs, which need the year the folder names."""
    source_year_id = path.parent.name
    if not years.check_source_year_id_is_valid(source_year_id):
        return [
            Problem(
                location="document",
                message="not in an academic year folder, so it is filed under no year",
                value=source_year_id,
            )
        ]
    year = years.get_year_from_source_year_id(source_year_id)
    return [
        Problem(location="document", message=defect)
        for defect in [
            *shows.get_show_date_defects(data, year),
            *shows.get_show_defects(data),
        ]
    ]


def get_rule_problems(
    document_type: ContentDocumentType, path: Path, data: Any
) -> list[Problem]:
    problems = []
    if document_type is SHOW:
        problems.extend(get_show_rule_problems(path, data))
        problems.extend(get_link_problems(data.links))
    if document_type is VENUE:
        problems.extend(get_link_problems(data.links))
    if document_type is PERSON:
        problems.extend(get_link_problems([*data.links, *data.news]))
    return problems


def get_link_problems(document_links: list) -> list[Problem]:
    return [
        Problem(location="links", message=defect)
        for defect in links.get_link_defects(document_links)
    ]


def read_document(
    document_type: ContentDocumentType, path: Path
) -> tuple[Any, list[Problem]]:
    """The authored data and any problem reading it, document or data file alike."""
    if path.parent.name == DATA_DIRECTORY:
        data, duplicate_keys = load_yaml_detecting_duplicates(path.read_text())
        return data, get_duplicate_key_problems(duplicate_keys)
    handler = DuplicateKeyDetectingYAMLHandler()
    document = frontmatter.load(path, handler=handler)
    metadata = {"id": path.stem, **document.metadata}
    return metadata, get_duplicate_key_problems(handler.duplicate_keys)


def build_model(document_type: ContentDocumentType, data: Any) -> Any:
    if isinstance(data, dict):
        return document_type.model(**data)
    model = document_type.model
    if not issubclass(model, BaseCollectionModel):
        raise TypeError(f"A {document_type.name} document must be a mapping")
    collection_model: type[BaseCollectionModel] = model
    return collection_model(data)


def check_file(path: Path) -> FileResult:
    """Validate one file, as `nthp load` would."""
    document_type = resolve_document_type(path)
    if document_type is None:
        return FileResult(
            path,
            None,
            [Problem("document", "not a content file the API knows how to read")],
        )
    try:
        data, problems = read_document(document_type, path)
    except yaml.YAMLError as error:
        return FileResult(path, document_type, [Problem("document", str(error))])
    except OSError as error:
        return FileResult(path, document_type, [Problem("document", str(error))])
    try:
        model = build_model(document_type, data)
    except ValidationError as error:
        return FileResult(
            path,
            document_type,
            [*problems, *make_validation_problems(error, document_type)],
        )
    return FileResult(
        path, document_type, [*problems, *get_rule_problems(document_type, path, model)]
    )


def check_files(paths: list[Path]) -> list[FileResult]:
    return [check_file(path) for path in expand_paths(paths)]
