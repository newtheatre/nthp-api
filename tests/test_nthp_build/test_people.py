import pytest

from nthp_build import people


@pytest.mark.parametrize(
    "input,expected",
    [("Fred Bloggs", "fred_bloggs"), ("Frëd Blöggs ", "fred_bloggs")],
)
def test_get_person_id(input: str, expected: str):
    assert people.get_person_id(input) == expected
