from pathlib import Path

from nthp_build.documents import DocumentPath


def get_year_id(year: int) -> str:
    return f"{str(year)[-2:]}_{str(year+1)[-2:]}"


def get_year_id_from_show_path(path: DocumentPath) -> str:
    return str(Path(path.id).parent)


def get_year_from_year_id(year_id: str) -> int:
    first_str, second_str = year_id.split("_")
    first, second = int(first_str), int(second_str)
    assert first == second - 1 or (first == 99 and second == 0)
    # TODO: Dear god, I'm writing Y2K-bugged code in 2021
    base = 2000 if first < 40 else 1900
    return base + first


def get_year_title(year: int) -> str:
    return f"{year}–{str(year + 1)[-2:]}"


def get_year_decade(year: int) -> int:
    assert len(str(year)) == 4
    return int(str(year)[:3])
