from typing import Any

import humps
import pytest

from nthp_api.nthp_build import content_schema, spec

SCHEMAS = spec.SPEC["components"]["schemas"]

FUZZY_DATE_REF = {"$ref": "#/components/schemas/FuzzyDate"}
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


def get_operations():
    return [
        operation
        for path_item in spec.SPEC["paths"].values()
        for operation in path_item.values()
    ]


def test_every_used_tag_is_declared_and_vice_versa():
    declared_tags = {tag["name"] for tag in spec.SPEC["tags"]}
    used_tags = {tag for operation in get_operations() for tag in operation["tags"]}
    assert used_tags == declared_tags


def find_keys(node: Any, key: str, path: str = "") -> list[str]:
    """Paths of every occurrence of the given key below the given node."""
    paths = []
    if isinstance(node, dict):
        if key in node:
            paths.append(path)
        for node_key, value in node.items():
            paths += find_keys(value, key, f"{path}.{node_key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            paths += find_keys(value, key, f"{path}[{index}]")
    return paths


def test_no_openapi_30_example_keyword():
    """OAS 3.1 takes JSON Schema `examples`, not the 3.0 `example` keyword."""
    assert find_keys(SCHEMAS, "example") == []


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

    def test_index_headshot_is_an_image_ref(self):
        assert {"$ref": "#/components/schemas/ImageRef"} in get_property(
            "PersonIndexItem", "headshot"
        )["anyOf"]

    def test_model_present(self):
        assert set(SCHEMAS["PersonIndexItem"]["properties"]) == {
            "id",
            "title",
            "submitted",
            "submittedDate",
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
            ("ShowDatedRef", "dateStart"),
            ("ShowDatedRef", "dateEnd"),
            ("Trivia", "submittedDate"),
        ],
    )
    def test_optional_fuzzy_date(self, model, field):
        assert get_property(model, field)["anyOf"] == [FUZZY_DATE_REF, NULL_SCHEMA]

    def test_named_component_carries_the_pattern_and_one_description(self):
        component = SCHEMAS["FuzzyDate"]
        assert component["type"] == "string"
        assert component["pattern"] == r"^\d{4}(-\d{2}(-\d{2})?)?$"
        assert "`YYYY-MM-DD`" in component["description"]

    def test_pattern_is_not_repeated_on_fields(self):
        """Every fuzzy date field refers to the one component."""
        assert find_keys(SCHEMAS, "pattern") == [".FuzzyDate"]

    def test_field_description_survives_beside_the_ref(self):
        day_precision = get_property("OnThisDayShow", "dateStart")
        assert day_precision == FUZZY_DATE_REF | {
            "title": "Date Start",
            "description": "First day of the run, always to day precision",
        }

    def test_person_submitted_is_a_boolean(self):
        assert get_property("PersonDetail", "submitted")["type"] == "boolean"
        assert get_property("PersonDetail", "submittedDate")["anyOf"] == [
            FUZZY_DATE_REF,
            NULL_SCHEMA,
        ]

    def test_trivia_submitted_example_shows_reduced_precision(self):
        assert get_property("Trivia", "submittedDate")["examples"] == ["2022-01"]

    def test_only_machine_timestamps_carry_a_date_format(self):
        """Content dates are fuzzy strings; only real timestamps keep a format."""
        assert find_formats(SCHEMAS) == {
            ".SiteStats.properties.buildTime": "date-time",
            ".Asset.properties.uploadedAt.anyOf[0]": "date-time",
        }


class TestPathParameters:
    @pytest.mark.parametrize(
        "path",
        [
            "/years/{id}.json",
            "/seasons/{id}.json",
            "/venues/{id}.json",
            "/people/{id}.json",
            "/collaborators/{id}.json",
            "/roles/committee/{id}.json",
            "/roles/crew/{id}.json",
            "/assets/album/{id}.json",
        ],
    )
    def test_records_are_addressed_by_id(self, path: str):
        [parameter] = spec.SPEC["paths"][path]["get"]["parameters"]
        assert parameter["name"] == "id"

    def test_shows_are_addressed_by_year_and_slug(self):
        """A show id contains a slash, which a single path parameter cannot hold."""
        operation = spec.SPEC["paths"]["/shows/{yearId}/{slug}.json"]["get"]
        assert operation["operationId"] == "getShowDetail"
        assert [parameter["name"] for parameter in operation["parameters"]] == [
            "yearId",
            "slug",
        ]
        assert all(
            parameter["in"] == "path" and parameter["required"]
            for parameter in operation["parameters"]
        )


class TestContentSchema:
    def test_path_present(self):
        operation = spec.SPEC["paths"]["/content-schema/{type}.json"]["get"]
        assert operation["operationId"] == "getContentSchema"
        assert operation["tags"] == ["content-schema"]

    def test_type_param_enumerates_document_types(self):
        [parameter] = spec.SPEC["paths"]["/content-schema/{type}.json"]["get"][
            "parameters"
        ]
        assert parameter["name"] == "type"
        assert parameter["schema"]["enum"] == [
            document_type.name
            for document_type in content_schema.CONTENT_DOCUMENT_TYPES
        ]

    def test_response_is_a_generic_json_schema_object(self):
        operation = spec.SPEC["paths"]["/content-schema/{type}.json"]["get"]
        response_schema = operation["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
        assert response_schema == {"type": "object"}


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
