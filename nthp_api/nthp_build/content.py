"""Rendering of authored markdown into the HTML and plaintext the API serves.

Content is editor-submitted, so the rendered HTML is sanitised here: the API is the
trust boundary, consumers render `content` fields as HTML without further defence.
"""

import html
import logging
from collections import Counter
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path

import markdown
import nh3
from markdown import Markdown

log = logging.getLogger(__name__)

ALLOWED_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "del",
    "dd",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "small",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "abbr": {"title"},
    "img": {"alt", "src", "title"},
    "td": {"align", "colspan", "rowspan"},
    "th": {"align", "colspan", "rowspan"},
}

ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

LINK_REL = "noopener noreferrer"

CLEAN_CONTENT_TAGS = {"script", "style"}

COMMENT_TOKEN = "<!-- -->"


class _MarkupInventory(HTMLParser):
    """Counts the tags, attributes and comments a fragment contains."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: Counter[str] = Counter()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tokens[f"<{tag}>"] += 1
        for name, _value in attrs:
            self.tokens[f"<{tag} {name}>"] += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_comment(self, data: str) -> None:
        self.tokens[COMMENT_TOKEN] += 1


def _markup_inventory(fragment: str) -> Counter[str]:
    parser = _MarkupInventory()
    parser.feed(fragment)
    parser.close()
    return parser.tokens


def _describe_removals(before: str, after: str) -> list[str]:
    """
    What sanitisation took out, as tag and attribute tokens.

    Comparing inventories rather than the raw strings keeps the parser's own
    normalisation, and the added link `rel`, from reading as a removal.
    """
    removed = _markup_inventory(before) - _markup_inventory(after)
    return sorted(removed.elements())


def sanitise_html(dirty: str, source_path: Path | str | None = None) -> str:
    """Sanitise rendered HTML, reporting anything the allow-list rejected."""
    clean = nh3.clean(
        dirty,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        clean_content_tags=CLEAN_CONTENT_TAGS,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel=LINK_REL,
    )
    if removals := _describe_removals(dirty, clean):
        log.error(
            "Removed disallowed markup from %s: %s",
            source_path or "content",
            ", ".join(removals),
        )
    return clean


def strip_markup(text: str) -> str:
    """
    Strip all markup from text destined for the search corpus.

    Removals go unreported: the same document's HTML is sanitised alongside, and
    reports the same content once.
    """
    return html.unescape(
        nh3.clean(
            text,
            tags=set(),
            attributes={},
            clean_content_tags=CLEAN_CONTENT_TAGS,
            link_rel=None,
        )
    )


def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


# Make a markdown parser that outputs plaintext
# Stole from https://stackoverflow.com/a/54923798/1345360
Markdown.output_formats["plain"] = unmark_element  # type: ignore
_markdown_unmarker = Markdown(output_format="plain")  # type: ignore
_markdown_unmarker.stripTopLevelTags = False  # type: ignore


def markdown_to_html(
    markdown_text: str | None, source_path: Path | str | None = None
) -> str | None:
    if not markdown_text:
        return None
    if not markdown_text.strip():
        return None
    rendered = sanitise_html(markdown.markdown(markdown_text), source_path)
    return rendered if rendered.strip() else None


def markdown_to_plaintext(markdown_text: str | None) -> str | None:
    if not markdown_text:
        return None
    if not markdown_text.strip():
        return None
    plaintext = strip_markup(_markdown_unmarker.convert(markdown_text))
    return plaintext if plaintext.strip() else None
