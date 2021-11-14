from collections import defaultdict
from typing import Dict, List, Tuple

from slugify import slugify

from nthp_build import database, schema


def get_playwright_id(name: str) -> str:
    return slugify(name, separator="_")


def save_playwright_show(playwright_name: str, show_id: str) -> None:
    database.PlaywrightShow.create(
        playwright_id=get_playwright_id(playwright_name),
        playwright_name=playwright_name,
        show_id=show_id,
    )


PlaywrightShowMapping = Dict[Tuple[str, str], List[database.Show]]


def get_playwright_shows() -> PlaywrightShowMapping:
    query = (
        database.PlaywrightShow.select(database.PlaywrightShow, database.Show)
        .join(
            database.Show,
            on=(database.PlaywrightShow.show_id == database.Show.id),
            attr="show",
        )
        .order_by(
            database.PlaywrightShow.playwright_id,
            database.Show.year,
            database.Show.date_start,
        )
    )
    playwright_shows = defaultdict(list)
    for result in query:
        playwright_shows[(result.playwright_id, result.playwright_name)].append(
            result.show
        )
    return playwright_shows


def get_playwright_list(
    playwright_shows: PlaywrightShowMapping,
) -> List[schema.PlaywrightListItem]:
    return [
        schema.PlaywrightListItem(
            id=id,
            name=name,
            shows=[
                schema.PlaywrightShowListItem(
                    id=show.id,
                    title=show.title,
                    date_start=show.date_start,
                    date_end=show.date_end,
                    primary_image=show.primary_image,
                )
                for show in shows
            ],
        )
        for (id, name), shows in playwright_shows.items()
    ]
