"""Every whole-document example must be a document the model would produce."""

import inspect
from typing import Any, Literal, get_args, get_origin

import pytest

from nthp_api.nthp_build import schema


def models_with_examples() -> list[type[schema.NthpSchema]]:
    return [
        model
        for _, model in inspect.getmembers(schema, inspect.isclass)
        if issubclass(model, schema.NthpSchema)
        and "examples" in (model.model_config.get("json_schema_extra") or {})
    ]


def test_the_detail_documents_carry_an_example():
    assert {model.__name__ for model in models_with_examples()} == {
        "OnThisDayShow",
        "PersonDetail",
        "SearchDocumentShow",
        "SeasonDetail",
        "ShowDetail",
        "SiteStats",
        "VenueDetail",
        "YearDetail",
    }


def as_model_input(
    model: type[schema.NthpSchema], example: dict[str, Any]
) -> dict[str, Any]:
    """A single-member `Literal` takes the enum member, not the string it dumps as."""
    literals = {
        field.alias or name: get_args(field.annotation)[0]
        for name, field in model.model_fields.items()
        if get_origin(field.annotation) is Literal
    }
    return example | {
        name: member for name, member in literals.items() if name in example
    }


@pytest.mark.parametrize(
    "model", models_with_examples(), ids=lambda model: model.__name__
)
def test_example_round_trips_through_the_model(model: type[schema.NthpSchema]):
    """The example validates, and is exactly what a dump of that record writes."""
    [example] = model.model_config["json_schema_extra"]["examples"]  # type: ignore[index,call-overload]
    record = model(**as_model_input(model, example))
    dumped = record.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert dumped == example
