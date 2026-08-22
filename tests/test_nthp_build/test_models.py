import datetime
import json

import pytest
from pydantic import ValidationError

from nthp_api.nthp_build import models
from nthp_api.nthp_build.fields import FuzzyDate


class TestAsset:
    def test_creation(self):
        assert models.Asset(type="poster", image="abc123")
        assert models.Asset(type="poster", video="abc123")
        assert models.Asset(type="poster", filename="abc123", title="hello")

    def test_slugify_type(self):
        assert models.Asset(type="poster", image="abc123").type == "poster"
        assert models.Asset(type="Poster", video="abc123").type == "poster"
        assert models.Asset(type="Set Design", video="abc123").type == "set-design"

    def test_require_image_xor_video_xor_filename(self):
        models.Asset(type="poster", image="abc123")
        models.Asset(type="poster", video="abc123")
        models.Asset(type="poster", filename="abc123", title="hello")

        with pytest.raises(ValidationError):
            models.Asset(type="poster")
        with pytest.raises(ValidationError):
            models.Asset(type="poster", image="abc123", video="abc123")
        with pytest.raises(ValidationError):
            models.Asset(
                type="poster",
                image="abc123",
                video="abc123",
                filename="abc123",
                title="def",
            )

    def test_require_title_with_filename(self):
        models.Asset(type="poster", filename="abc123", title="hello")
        with pytest.raises(ValidationError):
            models.Asset(type="poster", filename="abc123")

    def test_display_image_only_for_images(self):
        models.Asset(type="poster", image="abc", display_image=True)
        with pytest.raises(ValidationError):
            models.Asset(type="poster", filename="abc", display_image=True)


def make_show(**kwargs) -> models.Show:
    return models.Show(id="a_show", title="A Show", season="Spring", **kwargs)


class TestShowDates:
    def test_day_precision(self):
        show = make_show(date_start=datetime.date(2001, 6, 14))
        assert show.date_start == FuzzyDate(2001, 6, 14)

    def test_month_precision(self):
        show = make_show(date_start="2001-06", date_end="2001-07")
        assert show.date_start == FuzzyDate(2001, 6)
        assert show.date_end == FuzzyDate(2001, 7)

    def test_year_precision(self):
        assert make_show(date_start=2001).date_start == FuzzyDate(2001)

    def test_invalid_date(self):
        with pytest.raises(ValidationError):
            make_show(date_start="04/01/2017")

    def test_json_round_trip(self):
        show = make_show(date_start="2001-06")
        dumped = show.model_dump_json()
        assert json.loads(dumped)["date_start"] == "2001-06"
        assert models.Show(**json.loads(dumped)) == show


class TestLink:
    def test_year_precision_date(self):
        assert models.Link(type="review", date=2007).date == FuzzyDate(2007)


class TestTrivia:
    def test_month_precision_submitted(self):
        trivia = models.Trivia(quote="Something happened", submitted="2001-06")
        assert trivia.submitted == FuzzyDate(2001, 6)


class TestPersonSubmitted:
    @pytest.mark.parametrize("value", [True, False])
    def test_bool_stays_bool(self, value):
        person = models.Person(title="A Person", submitted=value)
        assert person.submitted is value

    def test_date(self):
        person = models.Person(title="A Person", submitted="2001-06")
        assert person.submitted == FuzzyDate(2001, 6)

    def test_year_precision(self):
        assert models.Person(title="A Person", submitted=2001).submitted == FuzzyDate(
            2001
        )

    def test_invalid_date(self):
        with pytest.raises(ValidationError):
            models.Person(title="A Person", submitted="04/01/2017")

    @pytest.mark.parametrize("value", [True, False])
    def test_bool_serialises_as_bool(self, value):
        person = models.Person(title="A Person", submitted=value)
        assert json.loads(person.model_dump_json())["submitted"] is value


class TestHistoryRecord:
    def test_creation(self):
        assert models.HistoryRecord(
            year="2020",
            academic_year="20_21",
            title="hello",
            description="world",
        )

    def test_no_academic_year(self):
        assert models.HistoryRecord(
            year="2020s",
            title="hello",
            description="world",
        )

    def test_blank_academic_year(self):
        with pytest.raises(ValidationError):
            models.HistoryRecord(
                year="2020s",
                academic_year="",
                title="hello",
                description="world",
            )

    def test_invalid_academic_year(self):
        with pytest.raises(ValidationError):
            models.HistoryRecord(
                year="2020",
                academic_year="2020_21",
                title="hello",
                description="world",
            )


class TestPerson:
    def test_course_coerced_to_list(self):
        assert models.Person(title="Fred Bloggs", course="English").course == [
            "English"
        ]
        assert models.Person(
            title="Fred Bloggs", course=["English", "Drama"]
        ).course == [
            "English",
            "Drama",
        ]
        assert models.Person(title="Fred Bloggs", course=None).course == []

    def test_careers_coerced_to_list(self):
        assert models.Person(title="Fred Bloggs", careers="Director").careers == [
            "Director"
        ]

    def test_career_alias_accepted(self):
        assert models.Person(title="Fred Bloggs", career=["Actor"]).careers == ["Actor"]

    def test_award(self):
        assert (
            models.Person(title="Fred Bloggs", award="Commendation").award
            == models.Award.COMMENDATION
        )
        assert models.Person(title="Fred Bloggs", award=None).award is None
        assert models.Person(title="Fred Bloggs", award="  ").award is None
        with pytest.raises(ValidationError):
            models.Person(title="Fred Bloggs", award="Knighthood")
