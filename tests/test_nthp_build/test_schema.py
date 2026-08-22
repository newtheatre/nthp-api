import inspect
import json
import types
import typing

import pytest

from nthp_api.nthp_build import schema
from nthp_api.nthp_build.fields import FuzzyDate

SCHEMA_MODELS = [
    model
    for _, model in inspect.getmembers(schema, inspect.isclass)
    if issubclass(model, schema.NthpSchema) and model is not schema.NthpSchema
]

# Every list model against the detail model it must be a subset of, narrowest first.
MODEL_FAMILIES = [
    (schema.ShowIndexItem, schema.ShowList),
    (schema.ShowList, schema.ShowDetail),
    (schema.PersonIndexItem, schema.PersonDetail),
    (schema.VenueList, schema.VenueDetail),
    (schema.SeasonList, schema.SeasonDetail),
    (schema.YearList, schema.YearDetail),
]


def unwrap_optional(annotation: object) -> tuple[object, bool]:
    """The annotation without its `| None`, and whether it had one."""
    if typing.get_origin(annotation) not in (types.UnionType, typing.Union):
        return annotation, False
    members = [
        member for member in typing.get_args(annotation) if member is not type(None)
    ]
    nullable = len(members) != len(typing.get_args(annotation))
    if len(members) == 1:
        return members[0], nullable
    return annotation, nullable


def is_nullable(annotation: object) -> bool:
    return unwrap_optional(annotation)[1]


def mentions_list(annotation: object) -> bool:
    if typing.get_origin(annotation) is list:
        return True
    return any(mentions_list(member) for member in typing.get_args(annotation))


def annotations_compatible(narrow: object, wide: object) -> bool:
    """
    Whether a detail model's annotation still satisfies the list model's.

    Identical types pass; so does a detail model carrying the richer model of a pair,
    as rule 4 has it, since `Asset` is an `ImageRef` with more on it.
    """
    if narrow == wide:
        return True
    narrow_type, narrow_null = unwrap_optional(narrow)
    wide_type, wide_null = unwrap_optional(wide)
    if narrow_null != wide_null:
        return False
    return (
        isinstance(narrow_type, type)
        and isinstance(wide_type, type)
        and issubclass(wide_type, narrow_type)
    )


class TestNullability:
    """Rule 8: nullable implies a default, so the spec's `required` is honest."""

    @pytest.mark.parametrize("model", SCHEMA_MODELS, ids=lambda model: model.__name__)
    def test_nullable_fields_have_a_default(self, model):
        required_and_nullable = [
            name
            for name, field in model.model_fields.items()
            if field.is_required() and is_nullable(field.annotation)
        ]
        assert required_and_nullable == []

    @pytest.mark.parametrize("model", SCHEMA_MODELS, ids=lambda model: model.__name__)
    def test_no_list_is_nullable(self, model):
        """Lists are always emitted, so none of them may be null."""
        nullable_lists = [
            name
            for name, field in model.model_fields.items()
            if is_nullable(field.annotation) and mentions_list(field.annotation)
        ]
        assert nullable_lists == []


class TestModelFamilies:
    """Rule 9: `XIndexItem` ⊂ `XList` ⊂ `XDetail`, same names, types and optionality."""

    @pytest.mark.parametrize(
        ("narrow", "wide"),
        MODEL_FAMILIES,
        ids=lambda model: model.__name__,
    )
    def test_narrow_model_is_a_subset(self, narrow, wide):
        for name, field in narrow.model_fields.items():
            assert name in wide.model_fields, f"{wide.__name__} lacks {name}"
            wide_field = wide.model_fields[name]
            assert annotations_compatible(field.annotation, wide_field.annotation), (
                f"{wide.__name__}.{name} has a different type"
            )
            assert field.is_required() == wide_field.is_required(), (
                f"{wide.__name__}.{name} differs in whether it is required"
            )


class TestPersonGraduated:
    def test_from_grad_year_1999_estimated(self):
        assert schema.PersonGraduated.from_grad_year(
            1999, estimated=True
        ) == schema.PersonGraduated(
            id="1998-99",
            title="1998-99",
            start_year=1998,
            grad_year=1999,
            decade=1990,
            estimated=True,
        )

    def test_from_grad_year_2000_actual(self):
        assert schema.PersonGraduated.from_grad_year(
            2000, estimated=False
        ) == schema.PersonGraduated(
            id="1999-00",
            title="1999-00",
            start_year=1999,
            grad_year=2000,
            decade=1990,
            estimated=False,
        )

    def test_from_grad_year_2001_estimated(self):
        assert schema.PersonGraduated.from_grad_year(
            2001, estimated=True
        ) == schema.PersonGraduated(
            id="2000-01",
            title="2000-01",
            start_year=2000,
            grad_year=2001,
            decade=2000,
            estimated=True,
        )


class TestDatesFromDatabase:
    """Date columns hold reduced ISO strings, schema models revalidate them."""

    @pytest.mark.parametrize("stored", ["2001", "2001-06", "2001-06-14"])
    def test_show_dates_round_trip(self, stored):
        show = schema.ShowList(
            id="1999-00/a_show",
            title="A Show",
            year_id="1999-00",
            year=1999,
            season="In House",
            devised=False,
            date_start=stored,
        )
        assert show.date_start == FuzzyDate.parse(stored)
        assert json.loads(show.model_dump_json(by_alias=True))["dateStart"] == stored

    def test_trivia_submitted_round_trip(self):
        trivia = schema.Trivia(quote="A quote", submitted_date="2001-06")
        assert trivia.submitted_date == FuzzyDate(2001, 6)
        assert (
            json.loads(trivia.model_dump_json(by_alias=True))["submittedDate"]
            == "2001-06"
        )

    def test_person_submission_is_a_flag_and_a_date(self):
        person = schema.PersonDetail(
            id="a_person",
            title="A Person",
            has_bio=True,
            submitted=True,
            submitted_date="2001-06",
            show_role_count=0,
            committee_role_count=0,
            student=False,
        )
        dumped = json.loads(person.model_dump_json(by_alias=True))
        assert dumped["submitted"] is True
        assert dumped["submittedDate"] == "2001-06"
