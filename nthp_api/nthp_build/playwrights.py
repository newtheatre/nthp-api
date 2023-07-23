from collections import defaultdict
from typing import NamedTuple

from slugify import slugify

from nthp_api.nthp_build import database, people, schema


def get_play_id(name: str) -> str:
    return slugify(name, separator="_")


def get_playwright_id(name: str) -> str:
    return slugify(name, separator="_")


def save_playwright_show(
    play_name: str, playwright_name: str, show_id: str, student_written: bool
) -> None:
    database.PlaywrightShow.create(
        play_id=get_play_id(play_name),
        play_name=play_name,
        playwright_id=get_playwright_id(playwright_name),
        playwright_name=playwright_name,
        show_id=show_id,
        person_id=people.get_person_id(playwright_name) if student_written else None,
    )


PlaywrightShowMapping = dict[tuple[str, str], list[database.Show]]


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
) -> list[schema.PlaywrightListItem]:
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


class PlayRef(NamedTuple):
    play_id: str
    play_name: str
    playwright_id: str
    playwright_name: str


PlayShowMapping = dict[PlayRef, list[database.Show]]


def get_play_shows() -> PlayShowMapping:
    query = (
        database.PlaywrightShow.select(database.PlaywrightShow, database.Show)
        .join(
            database.Show,
            on=(database.PlaywrightShow.show_id == database.Show.id),
            attr="show",
        )
        .order_by(
            database.PlaywrightShow.play_id,
            database.Show.year,
            database.Show.date_start,
        )
    )
    play_shows = defaultdict(list)
    for result in query:
        play_shows[
            PlayRef(
                play_id=result.play_id,
                play_name=result.play_name,
                playwright_id=result.playwright_id,
                playwright_name=result.playwright_name,
            )
        ].append(result.show)
    return play_shows


def get_play_list(
    play_shows: PlayShowMapping,
) -> list[schema.PlayListItem]:
    return [
        schema.PlayListItem(
            id=play_ref.play_id,
            title=play_ref.play_name,
            playwright=schema.Playwright(
                id=play_ref.playwright_id,
                name=play_ref.playwright_name,
            ),
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
        for play_ref, shows in play_shows.items()
    ]
