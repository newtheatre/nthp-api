from typing import Optional

import markdown


def markdown_to_html(markdown_text: Optional[str]) -> Optional[str]:
    if not markdown_text:
        return None
    if markdown_text.strip() == "":
        return None
    return markdown.markdown(markdown_text)
