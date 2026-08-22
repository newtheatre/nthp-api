import datetime

import pytest

from nthp_api.nthp_build import years
from nthp_api.nthp_build.config import get_current_year_end


@pytest.mark.parametrize(
    "today,expected",
    [
        (datetime.date(2026, 1, 1), 2026),
        (datetime.date(2026, 8, 31), 2026),
        (datetime.date(2026, 9, 1), 2027),
        (datetime.date(2026, 12, 31), 2027),
    ],
)
def test_get_current_year_end(today: datetime.date, expected: int):
    assert get_current_year_end(today) == expected


@pytest.mark.parametrize(
    "today,expected_last_year_id",
    [
        (datetime.date(2026, 8, 31), "2025-26"),
        (datetime.date(2026, 9, 1), "2026-27"),
    ],
)
def test_last_year_built_either_side_of_september(
    today: datetime.date, expected_last_year_id: str
):
    """`dump_years` uses `year_end` as an exclusive bound over start years."""
    years_built = range(1940, get_current_year_end(today))
    assert years.get_public_year_id(years_built[-1]) == expected_last_year_id
