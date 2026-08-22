from typing import Any

import humps
import pytest

from nthp_api.nthp_build import spec

SCHEMAS = spec.SPEC["components"]["schemas"]

FUZZY_DATE_SCHEMA = {"type": "string", "pattern": r"^\d{4}(-\d{2}(-\d{2})?)?$"}
NULL_SCHEMA = {"type": "null"}
BOOLEAN_SCHEMA = {"type": "boolean"}


def get_property(model: str, field: str) -> dict[str, Any]:
    return SCHEMAS[model]["properties"][field]


def find_formats(node: Any, path: str = "") -> dict[str, str]:
    """Map of path to the `format` of every schema below the given node."""
    formats = {}
    if isinstance(node, dict):
        if "format" in node:
            formats[path] = node["format"]
        for key, value in node.items():
            formats |= find_formats(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            formats |= find_formats(value, f"{path}[{index}]")
    return formats


def test_spec_generates():
    """Basic sanity checks"""
    assert spec.SPEC["openapi"] == "3.1.0"
    expected_number_of_paths = 2
    assert len(spec.SPEC["paths"]) > expected_number_of_paths
    expected_number_of_schema = 2
    assert len(SCHEMAS) > expected_number_of_schema


class TestPeopleIndex:
    def test_path_present(self):
        operation = spec.SPEC["paths"]["/people/index.json"]["get"]
        assert operation["operationId"] == "getPersonIndex"
        assert operation["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("PersonIndexCollection")

    def test_detail_headshot_is_an_asset(self):
        assert {"$ref": "#/components/schemas/Asset"} in get_property(
            "PersonDetail", "headshot"
        )["anyOf"]

    def test_model_present(self):
        assert set(SCHEMAS["PersonIndexItem"]["properties"]) == {
            "id",
            "title",
            "submitted",
            "headshot",
            "graduated",
            "showRoleCount",
            "committeeRoleCount",
            "hasBio",
        }


class TestFuzzyDateFields:
    @pytest.mark.parametrize(
        ("model", "field"),
        [
            ("ShowDetail", "dateStart"),
            ("ShowDetail", "dateEnd"),
            ("ShowList", "dateStart"),
            ("ShowList", "dateEnd"),
            ("PlaywrightShowListItem", "dateStart"),
            ("PlaywrightShowListItem", "dateEnd"),
            ("TargetedTrivia", "submitted"),
            ("PersonTrivia", "submitted"),
        ],
    )
    def test_optional_fuzzy_date(self, model, field):
        assert get_property(model, field)["anyOf"] == [FUZZY_DATE_SCHEMA, NULL_SCHEMA]

    def test_person_submitted_admits_boolean(self):
        assert get_property("PersonDetail", "submitted")["anyOf"] == [
            FUZZY_DATE_SCHEMA,
            BOOLEAN_SCHEMA,
            NULL_SCHEMA,
        ]

    def test_trivia_submitted_example_shows_reduced_precision(self):
        assert get_property("TargetedTrivia", "submitted")["example"] == "2022-01"

    def test_no_date_formats_remain(self):
        """Only the build time, a real timestamp, keeps a date format."""
        assert find_formats(SCHEMAS) == {".SiteStats.properties.buildTime": "date-time"}


class TestFieldTitles:
    def test_titles_from_field_names_not_aliases(self):
        assert get_property("ShowDetail", "dateStart")["title"] == "Date Start"
        assert get_property("ShowDetail", "dateEnd")["title"] == "Date End"

    def test_no_title_case_mangled_aliases(self):
        """Camelised aliases must not be title-cased into words like Datestart."""
        mangled = {
            f"{model}.{field}": prop["title"]
            for model, model_schema in SCHEMAS.items()
            for field, prop in model_schema.get("properties", {}).items()
            if humps.decamelize(field) != field and prop.get("title") == field.title()
        }
        assert mangled == {}
