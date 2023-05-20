from io import StringIO

import markdown
from markdown import Markdown


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


def markdown_to_html(markdown_text: str | None) -> str | None:
    if not markdown_text:
        return None
    if not markdown_text.strip():
        return None
    return markdown.markdown(markdown_text)


def markdown_to_plaintext(markdown_text: str | None) -> str | None:
    if not markdown_text:
        return None
    if not markdown_text.strip():
        return None
    return _markdown_unmarker.convert(markdown_text)
