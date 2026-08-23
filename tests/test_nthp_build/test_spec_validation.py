"""Spec correctness: mechanical OAS 3.1 validation, plus checks the validator
doesn't cover.
"""

from typing import Any

from openapi_spec_validator import validate

from nthp_api.nthp_build import spec

SPEC = spec.SPEC
SCHEMAS = SPEC["components"]["schemas"]


def test_spec_is_a_valid_openapi_3_1_document():
    validate(SPEC)


def get_operations() -> list[dict[str, Any]]:
    return [
        operation
        for path_item in SPEC["paths"].values()
        for operation in path_item.values()
    ]


def test_every_operation_has_summary_description_tags_and_operation_id():
    required = ("summary", "description", "tags", "operationId")
    incomplete = [
        f"{operation.get('operationId', operation)}: missing {missing}"
        for operation in get_operations()
        if (missing := [key for key in required if not operation.get(key)])
    ]
    assert incomplete == []


def test_every_200_response_has_a_schema():
    missing = [
        operation["operationId"]
        for operation in get_operations()
        if "schema"
        not in operation["responses"]["200"]["content"]["application/json"]
    ]
    assert missing == []


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


def test_no_example_keyword_in_components():
    """OAS 3.1 takes JSON Schema `examples`, not the 3.0 `example` keyword."""
    assert find_keys(SCHEMAS, "example") == []


def find_null_descriptions(node: Any, path: str = "") -> list[str]:
    paths = []
    if isinstance(node, dict):
        if node.get("description", "") is None:
            paths.append(path)
        for node_key, value in node.items():
            paths += find_null_descriptions(value, f"{path}.{node_key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            paths += find_null_descriptions(value, f"{path}[{index}]")
    return paths


def test_no_null_descriptions():
    assert find_null_descriptions(SPEC) == []
