import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NamedTuple

import frontmatter
import yaml

from nthp_api.nthp_build.config import settings

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

    return [
        doc_path
        for doc_path in map(
            map_path, (settings.content_root / Path(content_directory)).rglob("*.md")
        )
        if doc_path is not None
    ]


def load_document(path: Path) -> frontmatter.Post:
    return frontmatter.load(path)


def load_yaml(path: Path | str) -> Any:
    with (settings.content_root / Path(path)).open() as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError:
            log.exception("Error loading YAML file %s", path)
