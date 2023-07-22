import pytest

from nthp_api.nthp_build import assets, models


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            [
                models.Asset(type="frog", image="a"),
                models.Asset(type="poster", image="b"),
            ],
            "b",
        ),
        (
            [
                models.Asset(type="frog", image="a", display_image=True),
                models.Asset(type="poster", image="b"),
            ],
            "a",
        ),
        (
            [
                models.Asset(type="frog", image="a"),
                models.Asset(type="programme", image="b"),
                models.Asset(type="flyer", image="c"),
            ],
            "c",
        ),
        (
            [
                models.Asset(type="programme", image="b"),
            ],
            "b",
        ),
        (
            [
                models.Asset(type="Poster", image="a"),
                models.Asset(type="programme", image="b"),
                models.Asset(type="flyer", image="c"),
            ],
            "a",
        ),
        (
            [
                models.Asset(type="poster", filename="a", title="abc"),
                models.Asset(type="programme", image="b"),
                models.Asset(type="flyer", image="c"),
            ],
            "c",
        ),
    ],
)
def test_pick_show_primary_image(input: list[models.Asset], expected: str):
    assert assets.pick_show_primary_image(input) == expected
