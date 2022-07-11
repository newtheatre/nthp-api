import pytest

from nthp_build import venues


@pytest.mark.parametrize(
    "input,expected",
    [
        ("New Theatre", "new-theatre"),
        ("Nëd Thöoter ", "ned-thooter"),
        ("Lee Rosy's Tea Rooms", "lee-rosys-tea-rooms"),
    ],
)
def test_get_venue_id(input: str, expected: str):
    assert venues.get_venue_id(input) == expected
