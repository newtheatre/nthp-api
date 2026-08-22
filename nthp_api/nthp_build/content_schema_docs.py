"""
Renders the content schemas for people to read, as Markdown or as a page.

Both renderings are made from the same flattened tables, so the page and what
`nthp schema --format markdown` prints never disagree.
"""

import html
import json
from typing import Any, NamedTuple

from nthp_api.nthp_build.content_schema import (
    CONTENT_DOCUMENT_TYPES,
    RULES_KEYWORD,
    ContentDocumentType,
    get_document_schema,
)
from nthp_api.nthp_build.fields import FUZZY_DATE_PATTERN

SCALAR_TYPE_NAMES = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "null": "null",
}


class FieldRow(NamedTuple):
    name: str
    type: str
    required: bool
    description: str
    example: str


class Shape(NamedTuple):
    """One object shape: the document itself, or a shape nested inside it."""

    name: str
    title: str
    description: str
    rows: list[FieldRow]


def get_ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def describe_type(node: dict[str, Any]) -> str:
    """A readable type for a property, naming nested shapes rather than refs."""
    if "$ref" in node:
        return get_ref_name(node["$ref"])
    if "anyOf" in node:
        members = [
            describe_type(member)
            for member in node["anyOf"]
            if member.get("type") != "null"
        ]
        return " or ".join(dict.fromkeys(members)) or "null"
    node_type = node.get("type")
    if node_type == "array":
        return f"list of {describe_type(node.get('items', {}))}"
    if node_type == "string" and node.get("pattern") == FUZZY_DATE_PATTERN:
        return "date"
    if isinstance(node_type, str):
        return SCALAR_TYPE_NAMES.get(node_type, node_type)
    return "any"


def format_example(node: dict[str, Any]) -> str:
    examples = node.get("examples")
    if not examples:
        return ""
    example = examples[0]
    if isinstance(example, str):
        return example
    return json.dumps(example)


def describe_field(node: dict[str, Any]) -> str:
    """The field's title and its detail, as one sentence-led line."""
    return " — ".join(
        part
        for part in (node.get("title"), node.get("description"))
        if part is not None
    )


def make_field_rows(object_schema: dict[str, Any]) -> list[FieldRow]:
    required = set(object_schema.get("required", []))
    return [
        FieldRow(
            name=name,
            type=describe_type(node),
            required=name in required,
            description=describe_field(node),
            example=format_example(node),
        )
        for name, node in object_schema.get("properties", {}).items()
    ]


def make_shape(name: str, title: str, object_schema: dict[str, Any]) -> Shape:
    return Shape(
        name=name,
        title=title,
        description=object_schema.get("description", ""),
        rows=make_field_rows(object_schema),
    )


def get_root_shape(document_type: ContentDocumentType) -> Shape:
    """
    The shape one record of a document type takes.

    A data file is a list, so its record is the shape its items refer to; a
    document is that shape itself.
    """
    schema = get_document_schema(document_type)
    if schema.get("type") == "array":
        ref_name = get_ref_name(schema["items"]["$ref"])
        return make_shape(ref_name, document_type.title, schema["$defs"][ref_name])
    return make_shape(document_type.name, document_type.title, schema)


def get_nested_shapes(document_type: ContentDocumentType) -> dict[str, Shape]:
    """Every shape nested inside a document type, but not the record itself."""
    schema = get_document_schema(document_type)
    root_name = get_root_shape(document_type).name
    return {
        name: make_shape(name, name, definition)
        for name, definition in schema.get("$defs", {}).items()
        if name != root_name
    }


def get_shared_shape_names() -> set[str]:
    """Shapes more than one document type uses, so the page shows them once."""
    counts: dict[str, int] = {}
    for document_type in CONTENT_DOCUMENT_TYPES:
        for name in get_nested_shapes(document_type):
            counts[name] = counts.get(name, 0) + 1
    return {name for name, count in counts.items() if count > 1}


def get_shared_shapes() -> dict[str, Shape]:
    shared_names = get_shared_shape_names()
    shapes: dict[str, Shape] = {}
    for document_type in CONTENT_DOCUMENT_TYPES:
        for name, shape in get_nested_shapes(document_type).items():
            if name in shared_names:
                shapes.setdefault(name, shape)
    return dict(sorted(shapes.items()))


def get_rules(document_type: ContentDocumentType) -> list[str]:
    return list(get_document_schema(document_type).get(RULES_KEYWORD, []))


def render_markdown_table(rows: list[FieldRow]) -> list[str]:
    lines = [
        "| Field | Type | Required | Description | Example |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| `{row.name}` | {row.type} | {'yes' if row.required else ''} "
        f"| {row.description} | {f'`{row.example}`' if row.example else ''} |"
        for row in rows
    )
    return lines


def render_shape_markdown(shape: Shape, *, level: int) -> list[str]:
    lines = ["#" * level + f" {shape.title}", ""]
    if shape.description:
        lines.extend([shape.description, ""])
    lines.extend(render_markdown_table(shape.rows))
    lines.append("")
    return lines


def render_document_type_markdown(document_type: ContentDocumentType) -> str:
    """One document type, self-contained: its record and every shape below it."""
    schema = get_document_schema(document_type)
    lines = [f"# {document_type.title}", "", schema["description"], ""]
    rules = get_rules(document_type)
    if rules:
        lines.extend(["## Rules beyond the schema", ""])
        lines.extend(f"- {rule}" for rule in rules)
        lines.append("")
    lines.extend(["## Fields", ""])
    lines.extend(render_markdown_table(get_root_shape(document_type).rows))
    lines.append("")
    nested = get_nested_shapes(document_type)
    if nested:
        lines.extend(["## Shapes used above", ""])
        for shape in nested.values():
            lines.extend(render_shape_markdown(shape, level=3))
    return "\n".join(lines).rstrip() + "\n"


def render_markdown() -> str:
    return "\n".join(
        render_document_type_markdown(document_type)
        for document_type in CONTENT_DOCUMENT_TYPES
    )


PAGE_STYLE = """
:root { color-scheme: light dark; --rule: #8883; }
body { margin: 0 auto; padding: 2rem 1.5rem 6rem; max-width: 60rem;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  line-height: 1.5; }
h1 { font-size: 1.9rem; }
h2 { margin-top: 3rem; border-bottom: 1px solid var(--rule); padding-bottom: .3rem; }
h3 { margin-top: 2rem; font-size: 1.1rem; }
nav ul { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: .75rem; }
nav a { text-decoration: none; border: 1px solid var(--rule); border-radius: .4rem;
  padding: .2rem .6rem; }
code { font-size: .9em; }
p.location { font-family: ui-monospace, monospace; opacity: .8; }
.table-scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .92rem; }
th, td { text-align: left; vertical-align: top; padding: .4rem .6rem;
  border-bottom: 1px solid var(--rule); }
th { font-weight: 600; opacity: .75; font-size: .82rem;
  text-transform: uppercase; letter-spacing: .04em; }
td.required { white-space: nowrap; }
footer { margin-top: 4rem; opacity: .7; font-size: .9rem; }
"""


def render_html_table(rows: list[FieldRow]) -> str:
    header = (
        "<thead><tr><th>Field</th><th>Type</th><th>Required</th>"
        "<th>Description</th><th>Example</th></tr></thead>"
    )
    body = "".join(
        "<tr>"
        f"<td><code>{html.escape(row.name)}</code></td>"
        f"<td>{html.escape(row.type)}</td>"
        f"<td class='required'>{'yes' if row.required else ''}</td>"
        f"<td>{html.escape(row.description)}</td>"
        f"<td>{f'<code>{html.escape(row.example)}</code>' if row.example else ''}</td>"
        "</tr>"
        for row in rows
    )
    return (
        f"<div class='table-scroll'><table>{header}<tbody>{body}</tbody></table></div>"
    )


def render_html_shape(shape: Shape, *, shared: bool) -> str:
    anchor = f"shape-{shape.name}" if shared else f"nested-{shape.name}"
    parts = [f"<h3 id='{anchor}'>{html.escape(shape.title)}</h3>"]
    if shape.description:
        parts.append(f"<p>{html.escape(shape.description)}</p>")
    parts.append(render_html_table(shape.rows))
    return "".join(parts)


def render_html_document_type(
    document_type: ContentDocumentType, shared_names: set[str]
) -> str:
    parts = [
        f"<h2 id='{document_type.name}'>{html.escape(document_type.title)}</h2>",
        f"<p class='location'>{html.escape(document_type.location)}</p>",
        f"<p>{html.escape(document_type.description)}</p>",
    ]
    if document_type.body:
        parts.append(
            f"<p>The body below the front matter is "
            f"{html.escape(document_type.body)}</p>"
        )
    parts.append(
        f"<p>Schema: <a href='{document_type.filename}'>"
        f"<code>{document_type.filename}</code></a></p>"
    )
    rules = get_rules(document_type)
    if rules:
        parts.append("<h3>Rules beyond the schema</h3><ul>")
        parts.extend(f"<li>{html.escape(rule)}</li>" for rule in rules)
        parts.append("</ul>")
    parts.append(render_html_table(get_root_shape(document_type).rows))
    nested = {
        name: shape
        for name, shape in get_nested_shapes(document_type).items()
        if name not in shared_names
    }
    parts.extend(render_html_shape(shape, shared=False) for shape in nested.values())
    return "".join(parts)


def render_html() -> str:
    shared_shapes = get_shared_shapes()
    shared_names = set(shared_shapes)
    navigation = "".join(
        f"<li><a href='#{document_type.name}'>"
        f"{html.escape(document_type.title)}</a></li>"
        for document_type in CONTENT_DOCUMENT_TYPES
    ) + "".join(
        f"<li><a href='#shape-{name}'>{html.escape(name)}</a></li>"
        for name in shared_shapes
    )
    sections = "".join(
        render_html_document_type(document_type, shared_names)
        for document_type in CONTENT_DOCUMENT_TYPES
    )
    shared_section = (
        "<h2 id='shared-shapes'>Shared shapes</h2>"
        "<p>Shapes more than one document type uses.</p>"
        + "".join(
            render_html_shape(shape, shared=True) for shape in shared_shapes.values()
        )
    )
    return (
        "<!doctype html><html lang='en-GB'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Content schema — New Theatre History Project</title>"
        f"<style>{PAGE_STYLE}</style></head><body>"
        "<h1>Content schema</h1>"
        "<p>The shape of every file in the content repository, generated from the "
        "models the API loads them with. Each type links to its JSON Schema, which "
        "an editor can validate against; <code>nthp validate</code> checks a file "
        "against the same models and the rules below.</p>"
        f"<nav><ul>{navigation}</ul></nav>"
        f"{sections}{shared_section}"
        "<footer>Generated from the ingest models; do not edit by hand.</footer>"
        "</body></html>"
    )
