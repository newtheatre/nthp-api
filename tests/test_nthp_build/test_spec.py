from nthp_build import spec


def test_spec_generates():
    """Basic sanity checks"""
    assert spec.SPEC["openapi"] == "3.1.0"
    expected_number_of_paths = 2
    assert len(spec.SPEC["paths"]) > expected_number_of_paths
    expected_number_of_schema = 2
    assert len(spec.SPEC["components"]["schemas"]) > expected_number_of_schema
