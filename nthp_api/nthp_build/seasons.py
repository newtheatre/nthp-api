import logging
import re
from typing import NamedTuple

from nthp_api.nthp_build import database, schema, shows

log = logging.getLogger(__name__)

UNKNOWN_SEASON_NAME = "Unknown"
DISALLOWED_SLUG_CHARACTERS = re.compile(r"[^a-z0-9 -]")


class SeasonDefinition(NamedTuple):
    name: str
    aliases: set[str] = set()  # noqa: RUF012


SEASON_DEFINITIONS: list[SeasonDefinition] = [
    SeasonDefinition(name="In House"),
    SeasonDefinition(name="StuFF"),
    SeasonDefinition(
        name="Studio",
        aliases={
            "UNCUT",
            "Fringe",
        },
    ),
    SeasonDefinition(name="Edinburgh"),
    SeasonDefinition(name="External"),
    SeasonDefinition(name="Postgrads"),
    SeasonDefinition(name="Lakeside"),
    SeasonDefinition(name="Online"),
    SeasonDefinition(
        name="Creatives",
        aliases={
            "Unscripted",
        },
    ),
    SeasonDefinition(name="Fundraiser"),
    SeasonDefinition(name="Previews"),
    SeasonDefinition(name="IUDF"),
    SeasonDefinition(name="BedFest"),
    SeasonDefinition(
        name=UNKNOWN_SEASON_NAME,
        aliases={
            "unknown",
        },
    ),
]

SEASON_DEFINITION_MAP = {
    season_name: definition
    for definition in SEASON_DEFINITIONS
    for season_name in {definition.name} | definition.aliases
}


def slugify_season_name(season_name: str) -> str:
    """
    Slugify a season name as the old site's `_plugins/season.rb` `make_path` does.

    Downcase, drop anything but letters, digits, spaces and hyphens, spaces to
    hyphens, then collapse the triple hyphens a spaced hyphen leaves behind.
    """
    slug = DISALLOWED_SLUG_CHARACTERS.sub("", season_name.lower())
    return slug.replace(" ", "-").replace("---", "-")


def get_season_definition(season_name: str) -> SeasonDefinition | None:
    return SEASON_DEFINITION_MAP.get(season_name)


def get_season_id(definition: SeasonDefinition) -> str:
    return slugify_season_name(definition.name)


def get_show_season_id(season_name: str, source_path: str) -> str | None:
    """Resolve an authored season to its canonical id, aliases merged."""
    definition = get_season_definition(season_name)
    if definition is None:
        log.error(f"Unrecognised season {season_name!r} in {source_path}")
        return None
    return get_season_id(definition)


def get_season_shows(season_id: str) -> list[database.Show]:
    """
    Shows of a season, chronologically.

    Seasons span academic years, so `season_sort`, which only orders shows within a
    year, would scramble the list; date order is the only sensible one here.
    """
    return list(
        shows.get_show_query()
        .where(database.Show.season_id == season_id)  # type: ignore[attr-defined]
        .order_by(database.Show.date_start, database.Show.season_sort)
    )


def get_season_list(
    definition: SeasonDefinition, season_shows: list[database.Show]
) -> schema.SeasonList:
    return schema.SeasonList(
        id=get_season_id(definition),
        name=definition.name,
        aliases=sorted(definition.aliases),
        show_count=len(season_shows),
    )


def get_season_detail(
    definition: SeasonDefinition, season_shows: list[database.Show]
) -> schema.SeasonDetail:
    return schema.SeasonDetail(
        **get_season_list(definition, season_shows).model_dump(),
        shows=[shows.get_show_list_item(show_inst) for show_inst in season_shows],
    )
