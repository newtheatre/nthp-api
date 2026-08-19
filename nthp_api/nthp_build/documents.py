import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NamedTuple

import frontmatter
from frontmatter.default_handlers import YAMLHandler

from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.yaml_loader import DuplicateKey, load_yaml_detecting_duplicates

log = logging.getLogger(__name__)


class DocumentPath(NamedTuple):
    path: Path
    id: str
    content_path: Path
    filename: str
    basename: str


def find_documents(content_directory: Path | str) -> Iterable[DocumentPath]:
    def map_path(path: Path) -> DocumentPath | None:
        if path.name.startswith("_"):
            return None
        return DocumentPath(
            path=path,
            id=str(
                path.relative_to(settings.content_root / content_directory).parent
                / path.stem
            ).lstrip("_"),
            content_path=path.relative_to(settings.content_root),
            filename=path.name,
            basename=path.stem,
        )

    found_paths = sorted(
        (settings.content_root / Path(content_directory)).rglob("*.md")
    )
    return [doc_path for doc_path in map(map_path, found_paths) if doc_path is not None]


class DuplicateKeyDetectingYAMLHandler(YAMLHandler):
    def __init__(self) -> None:
        super().__init__()
        self.duplicate_keys: list[DuplicateKey] = []

    def load(self, fm: str, **kwargs: object) -> Any:
        data, self.duplicate_keys = load_yaml_detecting_duplicates(fm)
        return data


def _log_duplicate_keys(
    path: Path | str, duplicate_keys: Iterable[DuplicateKey]
) -> None:
    for duplicate_key in duplicate_keys:
        log.warning(
            "Duplicate key '%s' in %s (lines %d and %d); first value discarded",
            duplicate_key.key,
            path,
            duplicate_key.first_line,
            duplicate_key.duplicate_line,
        )


def load_document(path: Path) -> frontmatter.Post:
    handler = DuplicateKeyDetectingYAMLHandler()
    post = frontmatter.load(path, handler=handler)
    _log_duplicate_keys(path, handler.duplicate_keys)
    return post


def load_yaml(path: Path | str) -> Any:
    with (settings.content_root / Path(path)).open() as stream:
        data, duplicate_keys = load_yaml_detecting_duplicates(stream.read())
    _log_duplicate_keys(path, duplicate_keys)
    return data
