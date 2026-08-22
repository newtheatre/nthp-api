"""
Skeleton content files, generated from the same field metadata as the schema.

Every field appears, commented out with what it is for, so an author starts from
the whole shape and deletes what does not apply. The required fields are left
uncommented, so a skeleton saved unedited fails validation loudly rather than
quietly losing the record.
"""

import textwrap

from nthp_api.nthp_build import content_schema, content_schema_docs

COMMENT_WIDTH = 88
SKELETON_DOCUMENT_TYPES = ("show", "person", "venue")

# How an identifier spells the title, where the two are the same thing.
TITLE_SEPARATORS = {"person": "_", "venue": "-"}


def get_skeleton_document_types() -> list[content_schema.ContentDocumentType]:
    return [
        content_schema.DOCUMENT_TYPES_BY_NAME[name] for name in SKELETON_DOCUMENT_TYPES
    ]


def get_title_from_identifier(
    document_type: content_schema.ContentDocumentType, identifier: str
) -> str | None:
    """The title an identifier spells out, where the filename is the title."""
    separator = TITLE_SEPARATORS.get(document_type.name)
    if separator is None:
        return None
    return " ".join(word.capitalize() for word in identifier.split(separator))


def get_suggested_path(
    document_type: content_schema.ContentDocumentType, identifier: str
) -> str:
    directory, _, _filename = document_type.location.rpartition("/")
    return f"{directory}/{identifier}.md"


def wrap_comment(text: str, indent: str = "") -> list[str]:
    return textwrap.wrap(
        text,
        width=COMMENT_WIDTH,
        initial_indent=f"{indent}# ",
        subsequent_indent=f"{indent}#   ",
        break_long_words=False,
        break_on_hyphens=False,
    )


def get_nested_shape_name(row: content_schema_docs.FieldRow) -> str | None:
    """The shape a field holds, where it holds one rather than a scalar."""
    name = row.type.removeprefix("list of ")
    return name if name[:1].isupper() else None


def render_nested_entry(
    shape: content_schema_docs.Shape, *, is_list: bool
) -> list[str]:
    """The shape's own fields, commented, as one entry of a list or a mapping."""
    return [
        f"#   {'- ' if is_list and index == 0 else '  '}{row.name}:"
        for index, row in enumerate(shape.rows)
    ]


def render_field(
    row: content_schema_docs.FieldRow,
    nested_shapes: dict[str, content_schema_docs.Shape],
    value: str = "",
) -> list[str]:
    lines = wrap_comment(row.description)
    if row.example:
        lines.extend(wrap_comment(f"Example: {row.example}"))
    if row.required or value:
        lines.append(f"{row.name}:{f' {value}' if value else ''}")
        return lines
    lines.append(f"# {row.name}:")
    shape_name = get_nested_shape_name(row)
    if shape_name is not None and shape_name in nested_shapes:
        lines.extend(
            render_nested_entry(
                nested_shapes[shape_name], is_list=row.type.startswith("list of ")
            )
        )
    return lines


def render_header(
    document_type: content_schema.ContentDocumentType, identifier: str | None
) -> list[str]:
    location = (
        get_suggested_path(document_type, identifier)
        if identifier
        else document_type.location
    )
    return [
        *wrap_comment(f"{document_type.title} — save as {location}"),
        *wrap_comment(
            f"Every field is described at {content_schema.DOCUMENTATION_URL}"
        ),
        *wrap_comment("Delete what does not apply; uncomment what does."),
    ]


def render_skeleton(
    document_type: content_schema.ContentDocumentType, identifier: str | None = None
) -> str:
    """A skeleton document for an author to fill in."""
    shape = content_schema_docs.get_root_shape(document_type)
    nested_shapes = content_schema_docs.get_nested_shapes(document_type)
    title = get_title_from_identifier(document_type, identifier) if identifier else None
    lines = ["---", *render_header(document_type, identifier), ""]
    for row in shape.rows:
        if row.name in document_type.loader_supplied:
            continue
        value = title if row.name == "title" and title else ""
        lines.extend(render_field(row, nested_shapes, value=value or ""))
        lines.append("")
    lines.append("---")
    if document_type.body:
        lines.extend(["", f"<!-- {document_type.body.capitalize()} -->"])
    return "\n".join(lines) + "\n"
