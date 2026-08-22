"""Links to resources beyond the archive, as defined by the content repo."""

import functools
import logging
from pathlib import Path

from nthp_api.nthp_build import database, models, schema

log = logging.getLogger(__name__)

SNAPSHOT_BASE = "https://archive.is"
USERNAME_PLACEHOLDER = "???"


def validate_href(href: str | None) -> str | None:
    """
    Drop a URL with a scheme beyond the allow-list.

    `models.Link` rejects these at load time, with the path of the document that
    carries them, so nothing is logged here.
    """
    if href is None:
        return None
    scheme, separator, _rest = href.partition(":")
    if not separator or "/" in scheme or scheme == "":
        return href  # Relative URL, no scheme to check
    if scheme.lower() in models.ALLOWED_URL_SCHEMES:
        return href
    return None


def check_links(links: list[models.Link], content_path: Path) -> None:
    """
    Report links the definitions cannot resolve, as the document is loaded.

    A type that templates a username needs one to make an href at all, so a link
    without one resolves to whatever bare href it carries, if any.
    """
    for link in links:
        definition = get_link_type_definition(link.type)
        if definition is None or definition.href is None:
            continue
        if link.username is None:
            log.error(
                f"{content_path}: link of type {link.type!r} has no username, "
                f"though the type templates one"
            )


def save_link_type_definitions(
    definitions: models.LinkTypeDefinitionCollection,
) -> None:
    database.LinkTypeDefinition.insert_many(
        [
            {
                "name": definition.type,
                "sort": sort,
                "href_template": definition.href,
                "is_news": definition.is_news,
            }
            for sort, definition in enumerate(definitions)
        ]
    ).execute()


@functools.cache
def get_link_type_definitions() -> dict[str, models.LinkTypeDefinition]:
    """Link type definitions by lowercased name, as authored types vary in case."""
    return {
        inst.name.lower(): models.LinkTypeDefinition(
            type=inst.name, href=inst.href_template, is_news=inst.is_news
        )
        for inst in database.LinkTypeDefinition.select()
    }


def get_link_type_definition(type_name: str) -> models.LinkTypeDefinition | None:
    """
    The definition for an authored type, if the content repo defines one.

    Types are authored freely, so most links to niche services match no definition;
    those keep the authored type name. The `default` type carries nothing but an
    icon, so it is no use as a fallback.
    """
    return get_link_type_definitions().get(type_name.lower())


def get_link_href(
    link: models.Link, definition: models.LinkTypeDefinition | None
) -> str | None:
    """
    Resolve the link's URL, filling in a username where the type templates one.

    A type with a template and no username is a content error, reported at load
    time by `check_links`; the authored href, if any, stands in.
    """
    if definition is not None and definition.href is not None and link.username:
        return validate_href(
            definition.href.replace(USERNAME_PLACEHOLDER, link.username)
        )
    return validate_href(link.href)


def get_link_href_snapshot(link: models.Link) -> str | None:
    """The archive.is snapshot of the link, as the old site generated it."""
    if link.snapshot is None:
        return None
    return f"{SNAPSHOT_BASE}/{link.snapshot}"


def get_link(link: models.Link) -> schema.Link:
    definition = get_link_type_definition(link.type)
    return schema.Link(
        type=definition.type if definition else link.type,
        is_news=definition.is_news if definition else False,
        href=get_link_href(link, definition),
        href_snapshot=get_link_href_snapshot(link),
        username=link.username,
        title=link.title,
        date=link.date,
        publisher=link.publisher,
        rating=link.rating,
        quote=link.quote,
        note=link.note,
    )


def get_links(links: list[models.Link]) -> list[schema.Link]:
    return [get_link(link) for link in links]
