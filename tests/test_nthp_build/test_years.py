from pathlib import PosixPath

import pytest

from nthp_api.nthp_build import years
from nthp_api.nthp_build.documents import DocumentPath
from nthp_api.nthp_build.fields import FuzzyDate


@pytest.mark.parametrize(
    "input,expected",
    [
        (1940, "1940-41"),
        (1999, "1999-00"),
        (2000, "2000-01"),
        (2001, "2001-02"),
        (2039, "2039-40"),
    ],
)
def test_get_public_year_id(input: int, expected: str):
    assert years.get_public_year_id(input) == expected


def test_get_public_show_id():
    assert years.get_public_show_id(1973, "the_country_wife") == (
        "1973-74/the_country_wife"
    )


def test_get_source_year_id_from_show_path():
    path = DocumentPath(
        path=PosixPath("content/_shows/73_74/the_country_wife.md"),
        id="73_74/the_country_wife",
        content_path=PosixPath("_shows/73_74/the_country_wife.md"),
        filename="the_country_wife.md",
        basename="the_country_wife",
    )
    assert years.get_source_year_id_from_show_path(path) == "73_74"


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
def test_get_year_from_source_year_id(input: str, expected: int):
    assert years.get_year_from_source_year_id(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [(1940, "1940-41"), (1999, "1999-00"), (2000, "2000-01"), (2001, "2001-02")],
)
def test_get_year_title(input: int, expected: str):
    assert years.get_year_title(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (1940, 1940),
        (1949, 1940),
        (1950, 1950),
        (1999, 1990),
        (2000, 2000),
        (2001, 2000),
    ],
)
def test_get_year_decade(input: int, expected: int):
    assert years.get_year_decade(input) == expected


class TestCheckDateInYear:
    @pytest.mark.parametrize(
        "date",
        [
            FuzzyDate(2006, 9, 1),
            FuzzyDate(2007, 8, 31),
            FuzzyDate(2006),
            FuzzyDate(2007),
        ],
    )
    def test_dates_within_the_year(self, date: FuzzyDate):
        assert years.check_date_in_year(date, 2006)

    @pytest.mark.parametrize(
        "date", [FuzzyDate(2006, 8, 31), FuzzyDate(2007, 9, 1), FuzzyDate(2005)]
    )
    def test_dates_outside_the_year(self, date: FuzzyDate):
        assert not years.check_date_in_year(date, 2006)
