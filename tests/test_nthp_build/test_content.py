import pytest

from nthp_api.nthp_build import content

MARKDOWN_TEST_CASES = [
    (None, None, None),
    ("", None, None),
    ("1", "<p>1</p>", "1"),
    ("1\n1", "<p>1\n1</p>", "1\n1"),
    ("1\n\n1", "<p>1</p>\n<p>1</p>", "1\n1"),
    ("**1**", "<p><strong>1</strong></p>", "1"),
    ("# Hello", "<h1>Hello</h1>", "Hello"),
    ("# Hello\n123", "<h1>Hello</h1>\n<p>123</p>", "Hello\n123"),
]


@pytest.mark.parametrize(
    "input, expected",
    ((x[0], x[1]) for x in MARKDOWN_TEST_CASES),
)
def test_markdown_to_html(input: str | None, expected: str | None) -> None:
    assert content.markdown_to_html(input) == expected


@pytest.mark.parametrize(
    "input, expected",
    ((x[0], x[2]) for x in MARKDOWN_TEST_CASES),
)
def test_markdown_to_plaintext(input: str | None, expected: str | None) -> None:
    assert content.markdown_to_plaintext(input) == expected
