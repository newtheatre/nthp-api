import re
from pathlib import Path

from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.documents import DocumentPath

SOURCE_YEAR_ID_PATTERN = re.compile(r"^\d{2}_\d{2}$")
YEAR_FULL_LENGTH = 4
CENTURY = 100


def check_source_year_id_is_valid(source_year_id: str) -> bool:
    """Source ids are the content repo's academic year folders, e.g. `24_25`."""
    return SOURCE_YEAR_ID_PATTERN.match(source_year_id) is not None


def get_public_year_id(year: int) -> str:
    """The id every output document uses for an academic year, e.g. `2024-25`."""
    return f"{year}-{(year + 1) % CENTURY:02d}"


def get_public_show_id(year: int, show_basename: str) -> str:
    return f"{get_public_year_id(year)}/{show_basename}"


def get_source_year_id_from_show_path(path: DocumentPath) -> str:
    return str(Path(path.id).parent)


def get_year_from_source_year_id(source_year_id: str) -> int:
    """
    Resolve a two-digit source year id to a full year.

    The archive spans the century beginning at `year_start`, so the century is the
    one that places the year at or after `year_start`: with a 1940 start, `39_40`
    is 2039 and `40_41` is 1940. No dependency on the current date, so nothing
    changes as that century runs out.
    """
    assert check_source_year_id_is_valid(source_year_id)
    first_str, second_str = source_year_id.split("_")
    first, second = int(first_str), int(second_str)
    assert second == (first + 1) % CENTURY
    year = settings.year_start - settings.year_start % CENTURY + first
    return year if year >= settings.year_start else year + CENTURY


def get_year_title(year: int) -> str:
    return get_public_year_id(year)


def get_year_decade(year: int) -> int:
    assert len(str(year)) == YEAR_FULL_LENGTH
    return int(str(year)[:3])
