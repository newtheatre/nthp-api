import pytest

from nthp_build import models, schema, shows


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            dict(playwright="William Shakespeare", devised=False, improvised=False),
            schema.PlaywrightShow(
                id="william_shakespeare",
                type=schema.PlaywrightType.PLAYWRIGHT,
                name="William Shakespeare",
                descriptor="by William Shakespeare",
            ),
        ),
        (
            dict(playwright="unknown", devised=False, improvised=False),
            schema.Playwright(type=schema.PlaywrightType.UNKNOWN, descriptor="Unknown"),
        ),
        (
            dict(playwright="Various", devised=False, improvised=False),
            schema.Playwright(
                type=schema.PlaywrightType.VARIOUS, descriptor="Various Writers"
            ),
        ),
        (
            dict(playwright=None, devised=True, improvised=False),
            schema.Playwright(type=schema.PlaywrightType.DEVISED, descriptor="Devised"),
        ),
        (
            dict(playwright=None, devised="Cast", improvised=False),
            schema.Playwright(
                type=schema.PlaywrightType.DEVISED, descriptor="Devised by Cast"
            ),
        ),
        (
            dict(playwright=None, devised=False, improvised=True),
            schema.Playwright(
                type=schema.PlaywrightType.IMPROVISED, descriptor="Improvised"
            ),
        ),
        (
            dict(playwright=None, devised=False, improvised=False),
            None,
        ),
    ],
)
def test_get_show_playwright(input: dict, expected: schema.PlaywrightShow):
    show = models.Show.construct(**input)
    assert shows.get_show_playwright(show) == expected
