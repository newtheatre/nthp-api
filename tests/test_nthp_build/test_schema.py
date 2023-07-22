from nthp_api.nthp_build import schema


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
