import re
from pathlib import Path

from nthp_api.nthp_build.documents import DocumentPath

YEAR_ID_PATTERN = re.compile(r"^\d{2}_\d{2}$")
YEAR_FULL_LENGTH = 4
Y2K_1900_START = 40  # 40 should be 1940, 39 should be 2039
Y2K_1900_END = 99  # 99 should be 1999, 00 should be 2000


def check_year_id_is_valid(year_id: str) -> bool:
    return YEAR_ID_PATTERN.match(year_id) is not None


def get_year_id(year: int) -> str:
    return f"{str(year)[-2:]}_{str(year+1)[-2:]}"


def get_year_id_from_show_path(path: DocumentPath) -> str:
    return str(Path(path.id).parent)


def get_year_from_year_id(year_id: str) -> int:
    assert check_year_id_is_valid(year_id)
    first_str, second_str = year_id.split("_")
    first, second = int(first_str), int(second_str)
    assert first == second - 1 or (first == Y2K_1900_END and second == 0)
    # TODO: Dear god, I'm writing Y2K-bugged code in 2021
    base = 2000 if first < Y2K_1900_START else 1900
    return base + first


def get_year_title(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def get_year_decade(year: int) -> int:
    assert len(str(year)) == YEAR_FULL_LENGTH
    return int(str(year)[:3])
