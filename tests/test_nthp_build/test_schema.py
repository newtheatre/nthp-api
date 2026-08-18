import json

import pytest

from nthp_api.nthp_build import schema
from nthp_api.nthp_build.fields import FuzzyDate


class TestPersonGraduated:
    def test_from_year_1999_estimated(self):
        assert schema.PersonGraduated.from_year(
            1999, estimated=True
        ) == schema.PersonGraduated(
            year_title="1999", year_decade=199, year_id="98_99", estimated=True
        )

    def test_from_year_2000_actual(self):
        assert schema.PersonGraduated.from_year(
            2000, estimated=False
        ) == schema.PersonGraduated(
            year_title="2000", year_decade=199, year_id="99_00", estimated=False
        )

    def test_from_year_2001_estimated(self):
        assert schema.PersonGraduated.from_year(
            2001, estimated=True
        ) == schema.PersonGraduated(
            year_title="2001", year_decade=200, year_id="00_01", estimated=True
        )


class TestDatesFromDatabase:
    """Date columns hold reduced ISO strings, schema models revalidate them."""

    @pytest.mark.parametrize("stored", ["2001", "2001-06", "2001-06-14"])
    def test_show_dates_round_trip(self, stored):
        show = schema.ShowList(
            id="a_show", title="A Show", devised=False, date_start=stored
        )
        assert show.date_start == FuzzyDate.parse(stored)
        assert json.loads(show.model_dump_json(by_alias=True))["dateStart"] == stored

    def test_trivia_submitted_round_trip(self):
        trivia = schema.TargetedTrivia(
            quote="A quote", submitted="2001-06", person_id=None, person_name=None
        )
        assert trivia.submitted == FuzzyDate(2001, 6)
        assert json.loads(trivia.model_dump_json())["submitted"] == "2001-06"

    @pytest.mark.parametrize("submitted", [True, False, "2001-06"])
    def test_person_submitted(self, submitted):
        person = schema.PersonDetail(
            id="a_person",
            title="A Person",
            submitted=submitted,
            show_roles=[],
            committee_roles=[],
        )
        assert json.loads(person.model_dump_json())["submitted"] == submitted
