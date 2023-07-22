from pathlib import PosixPath

import pytest

from nthp_api.nthp_build import years
from nthp_api.nthp_build.documents import DocumentPath


@pytest.mark.parametrize(
    "input,expected",
    [(1940, "40_41"), (1999, "99_00"), (2000, "00_01"), (2001, "01_02")],
)
def test_get_year_id(input: int, expected: str):
    assert years.get_year_id(input) == expected


def test_get_year_id_from_show_path():
    path = DocumentPath(
        path=PosixPath("content/_shows/73_74/the_country_wife.md"),
        id="73_74/the_country_wife",
        content_path=PosixPath("_shows/73_74/the_country_wife.md"),
        filename="the_country_wife.md",
        basename="the_country_wife",
    )
    assert years.get_year_id_from_show_path(path) == "73_74"


@pytest.mark.parametrize(
    "input,expected",
    [
        ("40_41", 1940),
        ("99_00", 1999),
        ("00_01", 2000),
        ("01_02", 2001),
        ("39_40", 2039),
    ],
)
def test_get_year_from_year_id(input: str, expected: int):
    assert years.get_year_from_year_id(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [(1940, "1940-41"), (1999, "1999-00"), (2000, "2000-01"), (2001, "2001-02")],
)
def test_get_year_title(input: int, expected: str):
    assert years.get_year_title(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [(1940, 194), (1949, 194), (1950, 195), (1999, 199), (2000, 200), (2001, 200)],
)
def test_get_year_decade(input: int, expected: int):
    assert years.get_year_decade(input) == expected
