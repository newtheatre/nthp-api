from pathlib import Path
from typing import Iterable, NamedTuple, Optional, Union

import frontmatter


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

    return filter(
        lambda x: x is not None,
        map(map_path, (CONTENT_ROOT / Path(content_directory)).rglob("*.md")),
    )


def load_document(path: Path) -> frontmatter.Post:
    return frontmatter.load(path)
