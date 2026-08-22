"""
Locating the content repository, before anything that reads settings is imported.

`nthp validate` takes a path to a file rather than to the repository, and the
settings the rest of the build reads want the repository, so it has to be found
first — which means finding it without importing any of it.
"""

from pathlib import Path

DATA_DIRECTORY = "_data"


def find_content_root(path: Path) -> Path | None:
    """The repository a file belongs to, as the directory holding its `_data`."""
    for candidate in [path.resolve(), *path.resolve().parents]:
        if (candidate / DATA_DIRECTORY).is_dir():
            return candidate
    return None
