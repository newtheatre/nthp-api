from pathlib import PosixPath

import pytest

from nthp_build import years
from nthp_build.documents import DocumentPath


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
