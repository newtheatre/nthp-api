"""
JSON Schema for the content documents, generated from the ingest models.

The models are the source of truth for what the API accepts, so everything an
editor or an agent needs to know about the shape of a content file is generated
from them: the schemas an editor validates against, the page a human reads, and
the skeletons `nthp new` writes.

What the schema cannot say — that a date must fall inside the year its folder
names, that an alias needs a credit to attach to — is carried alongside it as
`x-nthp-rules`, one line per rule, taken from the checks that enforce them.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_collections import BaseCollectionModel

from nthp_api.nthp_build import models

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
RULES_KEYWORD = "x-nthp-rules"
REF_TEMPLATE = "#/$defs/{model}"

DOCUMENTATION_URL = "https://content.nthp.wjdp.uk/v1/nthp-api-master/content-schema/"


@dataclass(frozen=True)
class ContentDocumentType:
    """One kind of content file, and everything a person needs to author one."""

    name: str
    title: str
    model: type[BaseModel] | type[BaseCollectionModel]
    location: str
    description: str
    rules: tuple[str, ...] = ()
    # Fields the loader fills in from the document's path, so an author may leave
    # them out even though the model requires them.
    loader_supplied: frozenset[str] = field(default_factory=frozenset)
    body: str | None = None

    @property
    def filename(self) -> str:
        return f"{self.name}.json"

    @property
    def record_model(self) -> type[BaseModel]:
        """The model one record takes; a data file holds a list of them."""
        return getattr(self.model, "__element__", None) or self.model


SHOW = ContentDocumentType(
    name="show",
    title="Show",
    model=models.Show,
    location="_shows/<YY_YY>/<show_name>.md",
    description=(
        "One production. The folder is the academic year it ran in and the "
        "filename, without its extension, is the show's identifier within that "
        "year."
    ),
    body="a synopsis of the show, in Markdown.",
    rules=(
        "`date_end` must not be before `date_start`.",
        "`date_start` must fall inside the academic year the folder names.",
        (
            "A `devised` or `improvised` show must not also name a `playwright`; the "
            "playwright is dropped from the show and from every index."
        ),
        (
            "`playwright_alias` needs the show to generate a student writing credit, "
            "so it needs `student_written` and no `playwright_false`."
        ),
        (
            "`student_written` with a `playwright` naming several people generates no "
            "credit for any of them; credit each writer in `crew` and set "
            "`playwright_false`."
        ),
        (
            "`venue` is spelled into an identifier, so spell it identically across "
            "every show at that venue."
        ),
        (
            "`venue_sort` groups a show under its venue, so it does nothing without a "
            "`venue`."
        ),
        "`season` must be one the site knows, or the show appears in no season index.",
    ),
    loader_supplied=frozenset({"id"}),
)

PERSON = ContentDocumentType(
    name="person",
    title="Person",
    model=models.Person,
    location="_people/<firstname_lastname>.md",
    description=(
        "A person with a record of their own. Everyone credited on a show already "
        "gets a page; this document adds a biography and everything below to it. "
        "The filename is the person's identifier."
    ),
    body="a biography, in Markdown.",
    rules=(
        "`title` must match the filename: `Fred Bloggs` is `fred_bloggs.md`.",
        (
            "Two people whose names make the same identifier need an explicit `id` on "
            "one of them."
        ),
        (
            "`graduated` should fall between their first credit and ten years after "
            "their last."
        ),
        (
            "An `award` needs a `graduated` year, or credits it can be estimated from, "
            "or it appears on no year page."
        ),
    ),
    loader_supplied=frozenset({"id"}),
)

VENUE = ContentDocumentType(
    name="venue",
    title="Venue",
    model=models.Venue,
    location="_venues/<venue-name>.md",
    description=(
        "A venue with a record of its own. Venues named by shows alone are "
        "published as stubs; this document gives one a description, links and a "
        "location. The filename is the venue's identifier."
    ),
    body="a description of the venue, in Markdown.",
    rules=(
        (
            "The filename must be `title` slugified: `Nottingham New Theatre` is "
            "`nottingham-new-theatre.md`."
        ),
        "`title` must match how shows spell the venue, or the two do not join up.",
    ),
    loader_supplied=frozenset({"id"}),
)

COMMITTEE = ContentDocumentType(
    name="committee",
    title="Committee",
    model=models.Committee,
    location="_committees/<YY_YY>.md",
    description=(
        "One year's committee. The filename is the academic year the committee served."
    ),
    body="a note about the year, in Markdown.",
    rules=(
        (
            "Every entry needs a `role`; one left out, or set to `unknown`, appears in "
            "no role index."
        ),
    ),
    loader_supplied=frozenset({"id"}),
)

HISTORY = ContentDocumentType(
    name="history",
    title="Key events",
    model=models.HistoryRecordCollection,
    location="_data/history.yaml",
    description=(
        "The theatre's key events, as one list. Unlike the documents above this is "
        "a data file, so it is a YAML list with no Markdown body."
    ),
    rules=(
        (
            "`academic_year` must be a year the archive covers, or the event appears "
            "on no year page."
        ),
    ),
)

ROLES = ContentDocumentType(
    name="roles",
    title="Crew roles",
    model=models.CrewRoleDefinitionCollection,
    location="_data/roles.yaml",
    description=(
        "The crew roles the site knows, with the names credits use for each. A "
        "role credited but not defined here keeps its authored name but gets no "
        "role page of its own. Icons and the `show` flag are presentation "
        "concerns, which the API ignores."
    ),
)

LINK_TYPES = ContentDocumentType(
    name="link-types",
    title="Link types",
    model=models.LinkTypeDefinitionCollection,
    location="_data/link-types.yaml",
    description=(
        "The link types the site knows. A type used but not defined here still "
        "works, but gets no icon and no news handling. Icons and proofer flags "
        "are presentation concerns, which the API ignores."
    ),
)

CONTENT_DOCUMENT_TYPES: list[ContentDocumentType] = [
    SHOW,
    PERSON,
    VENUE,
    COMMITTEE,
    HISTORY,
    ROLES,
    LINK_TYPES,
]

DOCUMENT_TYPES_BY_NAME = {
    document_type.name: document_type for document_type in CONTENT_DOCUMENT_TYPES
}


def get_document_schema(document_type: ContentDocumentType) -> dict[str, Any]:
    """The JSON Schema for one document type, ready to write out."""
    generated = document_type.model.model_json_schema(ref_template=REF_TEMPLATE)
    generated.pop("title", None)
    generated.pop("description", None)
    schema: dict[str, Any] = {
        "$schema": JSON_SCHEMA_DIALECT,
        "$id": document_type.filename,
        "title": document_type.title,
        "description": describe_document_type(document_type),
        **generated,
    }
    if document_type.rules:
        schema[RULES_KEYWORD] = list(document_type.rules)
    if document_type.loader_supplied and "required" in schema:
        schema["required"] = [
            name
            for name in schema["required"]
            if name not in document_type.loader_supplied
        ]
    return schema


def describe_document_type(document_type: ContentDocumentType) -> str:
    parts = [f"{document_type.location} — {document_type.description}"]
    if document_type.body:
        parts.append(f"The body below the front matter is {document_type.body}")
    return " ".join(parts)


def get_document_schemas() -> dict[str, dict[str, Any]]:
    return {
        document_type.name: get_document_schema(document_type)
        for document_type in CONTENT_DOCUMENT_TYPES
    }


def write_document_schemas(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for document_type in CONTENT_DOCUMENT_TYPES:
        path = directory / document_type.filename
        with path.open("w") as f:
            json.dump(
                get_document_schema(document_type), f, indent=2, ensure_ascii=False
            )
            f.write("\n")
