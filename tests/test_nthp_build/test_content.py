from typing import Optional

import pytest

from nthp_build import content


@pytest.mark.parametrize(
    "input, expected",
    [
        (None, None),
        ("", None),
        ("1", "<p>1</p>"),
        ("1\n1", "<p>1\n1</p>"),
        ("1\n\n1", "<p>1</p>\n<p>1</p>"),
    ],
)
def test_markdown_to_html(input: Optional[str], expected: Optional[str]) -> None:
    assert content.markdown_to_html(input) == expected
