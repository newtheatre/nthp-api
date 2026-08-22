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
    [(x[0], x[1]) for x in MARKDOWN_TEST_CASES],
)
def test_markdown_to_html(input: str | None, expected: str | None) -> None:
    assert content.markdown_to_html(input) == expected


@pytest.mark.parametrize(
    "input, expected",
    [(x[0], x[2]) for x in MARKDOWN_TEST_CASES],
)
def test_markdown_to_plaintext(input: str | None, expected: str | None) -> None:
    assert content.markdown_to_plaintext(input) == expected


class TestSanitisation:
    @pytest.mark.parametrize(
        "input, expected",
        [
            ("<script>alert(1)</script>Hi", "\n<p>Hi</p>"),
            ('<p onclick="alert(1)">Hi</p>', "<p>Hi</p>"),
            ("[x](javascript:alert(1))", '<p><a rel="noopener noreferrer">x</a></p>'),
            ("<iframe src='http://evil.example'></iframe>", None),
            ("Hi <!-- a comment --> there", "<p>Hi  there</p>"),
            ("<style>p{}</style>Hi", "\n<p>Hi</p>"),
            (
                "[x](data:text/html;base64,abc)",
                '<p><a rel="noopener noreferrer">x</a></p>',
            ),
        ],
    )
    def test_strips_disallowed_markup(self, input: str, expected: str | None) -> None:
        assert content.markdown_to_html(input) == expected

    @pytest.mark.parametrize(
        "input, expected",
        [
            ("<script>alert(1)</script>Hi", "\nHi"),
            ("Hi <!-- a comment --> there", "Hi  there"),
            ("<!-- only a comment -->", None),
        ],
    )
    def test_strips_markup_from_plaintext(
        self, input: str, expected: str | None
    ) -> None:
        assert content.markdown_to_plaintext(input) == expected

    def test_keeps_ordinary_markup(self) -> None:
        assert content.markdown_to_html(
            "**bold** [link](https://example.com) *and* `code`\n\n- one\n- two"
        ) == (
            '<p><strong>bold</strong> <a href="https://example.com" '
            'rel="noopener noreferrer">link</a> <em>and</em> <code>code</code></p>\n'
            "<ul>\n<li>one</li>\n<li>two</li>\n</ul>"
        )

    def test_keeps_mailto_links(self) -> None:
        assert content.markdown_to_html("<mailto:a@example.com>") == (
            '<p><a href="mailto:a@example.com" rel="noopener noreferrer">'
            "a@example.com</a></p>"
        )

    def test_logs_removals_with_document_path(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        content.markdown_to_html("<script>alert(1)</script>Hi", "_people/a_person.md")
        assert "_people/a_person.md" in caplog.text
        assert "<script>" in caplog.text
        assert caplog.records[0].levelname == "ERROR"

    def test_does_not_log_for_clean_content(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        content.markdown_to_html("**bold** [link](https://example.com)", "a.md")
        assert caplog.records == []
