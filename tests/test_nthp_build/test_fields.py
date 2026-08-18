import datetime

import pytest
from pydantic import BaseModel, ValidationError

from nthp_api.nthp_build.fields import FuzzyDate


class FuzzyDateModel(BaseModel):
    date: FuzzyDate


class TestFuzzyDateParse:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (datetime.date(2001, 6, 14), FuzzyDate(2001, 6, 14)),
            (2007, FuzzyDate(2007)),
            ("2007", FuzzyDate(2007)),
            ("2001-06", FuzzyDate(2001, 6)),
            ("2001-06-14", FuzzyDate(2001, 6, 14)),
            (FuzzyDate(2001, 6), FuzzyDate(2001, 6)),
        ],
    )
    def test_accepts(self, value, expected):
        assert FuzzyDate.parse(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (FuzzyDate(2007), "2007"),
            (FuzzyDate(2001, 6), "2001-06"),
            (FuzzyDate(2001, 6, 14), "2001-06-14"),
            (FuzzyDate(2001, 6, 4), "2001-06-04"),
        ],
    )
    def test_str(self, value, expected):
        assert str(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            True,
            False,
            datetime.datetime(2001, 6, 14, 12, 30),
            1899,
            2101,
            "1899",
            "2101",
            "2007-13",
            "2001-06-31",
            "04/01/2017",
            "",
            "2001-6",
            None,
            1.5,
        ],
    )
    def test_rejects(self, value):
        with pytest.raises(ValueError):
            FuzzyDate.parse(value)

    def test_rejects_day_without_month(self):
        with pytest.raises(ValueError):
            FuzzyDate(2001, None, 14)


class TestFuzzyDatePeriod:
    @pytest.mark.parametrize(
        ("value", "earliest", "latest"),
        [
            (FuzzyDate(2001), datetime.date(2001, 1, 1), datetime.date(2001, 12, 31)),
            (FuzzyDate(2001, 6), datetime.date(2001, 6, 1), datetime.date(2001, 6, 30)),
            (FuzzyDate(2000, 2), datetime.date(2000, 2, 1), datetime.date(2000, 2, 29)),
            (
                FuzzyDate(2001, 6, 14),
                datetime.date(2001, 6, 14),
                datetime.date(2001, 6, 14),
            ),
        ],
    )
    def test_earliest_latest(self, value, earliest, latest):
        assert value.earliest() == earliest
        assert value.latest() == latest


class TestFuzzyDateOrdering:
    def test_mixed_precision_sort(self):
        dates = [
            FuzzyDate(2002),
            FuzzyDate(2001, 6, 14),
            FuzzyDate(2001),
            FuzzyDate(2001, 12),
            FuzzyDate(2001, 6),
        ]
        assert sorted(dates) == [
            FuzzyDate(2001),
            FuzzyDate(2001, 6),
            FuzzyDate(2001, 6, 14),
            FuzzyDate(2001, 12),
            FuzzyDate(2002),
        ]

    def test_comparisons(self):
        assert FuzzyDate(2001) < FuzzyDate(2001, 6)
        assert FuzzyDate(2001, 6) <= FuzzyDate(2001, 6)
        assert FuzzyDate(2001, 6, 14) > FuzzyDate(2001, 6)
        assert FuzzyDate(2002) >= FuzzyDate(2001, 12, 31)

    def test_hashable(self):
        assert {FuzzyDate(2001, 6), FuzzyDate(2001, 6), FuzzyDate(2001)} == {
            FuzzyDate(2001),
            FuzzyDate(2001, 6),
        }


class TestFuzzyDatePydantic:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (datetime.date(2001, 6, 14), FuzzyDate(2001, 6, 14)),
            (2007, FuzzyDate(2007)),
            ("2001-06", FuzzyDate(2001, 6)),
        ],
    )
    def test_validation(self, value, expected):
        assert FuzzyDateModel(date=value).date == expected

    @pytest.mark.parametrize("value", [True, "2007-13", 1899])
    def test_validation_errors(self, value):
        with pytest.raises(ValidationError):
            FuzzyDateModel(date=value)

    @pytest.mark.parametrize(
        "value", [FuzzyDate(2007), FuzzyDate(2001, 6), FuzzyDate(2001, 6, 14)]
    )
    def test_json_round_trip(self, value):
        model = FuzzyDateModel(date=value)
        assert model.model_dump_json() == f'{{"date":"{value}"}}'
        assert FuzzyDateModel.model_validate_json(model.model_dump_json()) == model

    def test_json_schema(self):
        assert FuzzyDateModel.model_json_schema()["properties"]["date"] == {
            "type": "string",
            "pattern": r"^\d{4}(-\d{2}(-\d{2})?)?$",
            "title": "Date",
        }
