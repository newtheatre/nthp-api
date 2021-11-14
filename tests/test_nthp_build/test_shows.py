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
                student_written=False,
                person_id=None,
            ),
        ),
        (
            dict(
                playwright="Fred Bloggs",
                devised=False,
                improvised=False,
                student_written=True,
            ),
            schema.PlaywrightShow(
                id="fred_bloggs",
                type=schema.PlaywrightType.PLAYWRIGHT,
                name="Fred Bloggs",
                descriptor="by Fred Bloggs",
                student_written=True,
                person_id="fred_bloggs",
            ),
        ),
        (
            dict(playwright="unknown", devised=False, improvised=False),
            schema.PlaywrightShow(
                type=schema.PlaywrightType.UNKNOWN,
                descriptor="Unknown",
                student_written=False,
            ),
        ),
        (
            dict(playwright="Various", devised=False, improvised=False),
            schema.PlaywrightShow(
                type=schema.PlaywrightType.VARIOUS,
                descriptor="Various Writers",
                student_written=False,
            ),
        ),
        (
            dict(playwright=None, devised=True, improvised=False),
            schema.PlaywrightShow(
                type=schema.PlaywrightType.DEVISED,
                descriptor="Devised",
                student_written=False,
            ),
        ),
        (
            dict(playwright=None, devised="Someone", improvised=False),
            schema.PlaywrightShow(
                type=schema.PlaywrightType.DEVISED,
                descriptor="Devised by Someone",
                student_written=False,
            ),
        ),
        (
            dict(
                playwright=None, devised="Cast", improvised=False, student_written=True
            ),
            schema.PlaywrightShow(
                type=schema.PlaywrightType.DEVISED,
                descriptor="Devised by Cast",
                student_written=True,
            ),
        ),
        (
            dict(playwright=None, devised=False, improvised=True),
            schema.PlaywrightShow(
                type=schema.PlaywrightType.IMPROVISED,
                descriptor="Improvised",
                student_written=False,
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
