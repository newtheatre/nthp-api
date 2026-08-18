#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "PyYAML>=6.0,<7",
#   "rich>=14.0,<15",
# ]
# ///

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table
from rich.text import Text

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIRECTORY = REPO_ROOT / "docs"

MIN_WIDTH_FOR_TITLES = 120

TYPE_COLOURS = {
    "reference": "bright_cyan",
    "review": "bright_magenta",
    "task": "bright_blue",
}

STATE_COLOURS = {
    "done": "bold bright_green",
    "open": "bold bright_yellow",
    "planned": "bright_cyan",
    "todo": "bold bright_red",
}


@dataclass(frozen=True)
class Document:
    path: Path
    title: str
    document_type: str | None
    state: str | None
    error: str | None = None


def read_document(path: Path) -> Document:
    contents = path.read_text(encoding="utf-8")
    title = read_title(contents) or path.stem

    try:
        frontmatter = read_frontmatter(contents)
    except yaml.YAMLError as error:
        return Document(path, title, None, None, str(error))

    document_type = metadata_value(frontmatter, "type")
    state = metadata_value(frontmatter, "status") or metadata_value(
        frontmatter, "state"
    )
    return Document(path, title, document_type, state)


def read_frontmatter(contents: str) -> dict[str, Any]:
    lines = contents.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    try:
        closing_line = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration:
        return {}

    parsed = yaml.safe_load("\n".join(lines[1:closing_line])) or {}
    return parsed if isinstance(parsed, dict) else {}


def read_title(contents: str) -> str | None:
    for line in contents.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return None


def metadata_value(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    return str(value).strip().lower() if value is not None else None


def styled_value(value: str | None, colours: dict[str, str]) -> Text:
    if value is None:
        return Text("—", style="dim")
    return Text(value, style=colours.get(value, "white"))


def document_path(path: Path) -> Text:
    relative = path.relative_to(REPO_ROOT)
    return Text(str(relative), style=f"bold link file://{path}")


def render_documents(documents: list[Document]) -> None:
    console = Console()
    show_titles = console.width >= MIN_WIDTH_FOR_TITLES
    table = Table(
        title=f"Lumina documentation · {len(documents)} files",
        title_style="bold bright_white",
        header_style="bold white on dark_blue",
        border_style="bright_black",
        row_styles=["none", "on grey7"],
        show_lines=False,
    )
    table.add_column("Document", style="bold", no_wrap=True, overflow="ellipsis")
    table.add_column("Type", width=9, no_wrap=True)
    table.add_column("State", width=8, no_wrap=True)
    if show_titles:
        table.add_column("Title", overflow="fold", ratio=1)

    for document in documents:
        row = [
            document_path(document.path),
            styled_value(document.document_type, TYPE_COLOURS),
            styled_value(document.state, STATE_COLOURS),
        ]
        if show_titles:
            row.append(Text(document.title, style="bright_white"))
        table.add_row(*row)

    console.print()
    console.print(table)

    invalid = [document for document in documents if document.error]
    for document in invalid:
        console.print(
            "[bold red]Invalid frontmatter[/bold red] "
            f"[white]{document.path.relative_to(REPO_ROOT)}[/white]: "
            f"[dim]{document.error}[/dim]"
        )

    missing_type = sum(document.document_type is None for document in documents)
    missing_state = sum(document.state is None for document in documents)
    console.print(
        f"\n[dim]{missing_type} without a type · {missing_state} without a state[/dim]"
    )


def main() -> None:
    documents = [
        read_document(path)
        for path in sorted(
            DOCS_DIRECTORY.rglob("*.md"), key=lambda path: str(path).lower()
        )
    ]
    render_documents(documents)


if __name__ == "__main__":
    main()
