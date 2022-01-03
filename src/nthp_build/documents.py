from pathlib import Path
from typing import Any, Iterable, NamedTuple, Optional, Union

import frontmatter
import yaml


class DocumentPath(NamedTuple):
    path: Path
    id: str
    content_path: Path
    filename: str
    basename: str


CONTENT_ROOT = Path("content")


def find_documents(content_directory: Union[Path, str]) -> Iterable[DocumentPath]:
    def map_path(path: Path) -> Optional[DocumentPath]:
        if path.name.startswith("_"):
            return None
        return DocumentPath(
            path=path,
            id=str(
                path.relative_to(CONTENT_ROOT / content_directory).parent / path.stem
            ).lstrip("_"),
            content_path=path.relative_to(CONTENT_ROOT),
            filename=path.name,
            basename=path.stem,
        )

    return [
        doc_path
        for doc_path in map(
            map_path, (CONTENT_ROOT / Path(content_directory)).rglob("*.md")
        )
        if doc_path is not None
    ]


def load_document(path: Path) -> frontmatter.Post:
    return frontmatter.load(path)


def load_yaml(path: Union[Path, str]) -> Any:
    with open(CONTENT_ROOT / Path(path), "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
