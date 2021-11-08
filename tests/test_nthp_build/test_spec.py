from nthp_build import spec


def test_spec_generates():
    """Basic sanity checks"""
    assert spec.SPEC["openapi"] == "3.1.0"
    assert len(spec.SPEC["paths"]) > 2
    assert len(spec.SPEC["components"]["schemas"]) > 2
