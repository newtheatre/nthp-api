"""Data the site's homepage draws on: on this day, and the poster pool."""

import calendar
import datetime
from collections import defaultdict

from nthp_api.nthp_build import assets, database, schema, shows
from nthp_api.nthp_build.fields import FuzzyDate

DayOfYear = tuple[int, int]
LEAP_YEAR = 2000


def get_days_of_year() -> list[DayOfYear]:
    """Every day a show could fall on, the leap day included."""
    return [
        (month, day)
        for month in range(1, 13)
        for day in range(1, calendar.monthrange(LEAP_YEAR, month)[1] + 1)
    ]


def get_day_of_year_id(day_of_year: DayOfYear) -> str:
    month, day = day_of_year
    return f"{month:02d}-{day:02d}"


def get_show_run(
    show_inst: database.Show,
) -> tuple[FuzzyDate, FuzzyDate | None] | None:
    """
    The run of a show as two day-precision dates, or None if it has no such run.

    Shows dated only to the month or year cannot be placed on a day, so they are
    left out. An end date before the start date is bad data: the show is kept, but
    read as running for the single day it starts on.
    """
    if show_inst.date_start is None:
        return None
    date_start = FuzzyDate.parse(show_inst.date_start)
    if date_start.day is None:
        return None
    if show_inst.date_end is None:
        return date_start, None
    date_end = FuzzyDate.parse(show_inst.date_end)
    if date_end.latest() < date_start.earliest():
        # Reported at load time, with the path of the document at fault.
        return date_start, None
    return date_start, date_end


def get_run_days_of_year(
    date_start: FuzzyDate, date_end: FuzzyDate | None
) -> set[DayOfYear]:
    """Every day of the year the run covers, inclusive of both ends."""
    first = date_start.earliest()
    last = date_end.latest() if date_end is not None else date_start.latest()
    return {
        (date.month, date.day)
        for date in (
            first + datetime.timedelta(days=offset)
            for offset in range((last - first).days + 1)
        )
    }


def get_on_this_day_show(
    show_inst: database.Show, date_start: FuzzyDate, date_end: FuzzyDate | None
) -> schema.OnThisDayShow:
    return schema.OnThisDayShow(
        id=show_inst.id,
        title=show_inst.title,
        year_id=show_inst.year_id,
        year=show_inst.year,
        primary_image=assets.get_image_ref(show_inst.primary_image),
        date_start=date_start,
        date_end=date_end,
    )


def get_shows_by_day_of_year() -> dict[DayOfYear, list[schema.OnThisDayShow]]:
    """Shows keyed by every day of the year they were running on."""
    shows_by_day: dict[DayOfYear, list[schema.OnThisDayShow]] = defaultdict(list)
    for show_inst in shows.get_show_query():
        run = get_show_run(show_inst)
        if run is None:
            continue
        date_start, date_end = run
        on_this_day_show = get_on_this_day_show(show_inst, date_start, date_end)
        for day_of_year in get_run_days_of_year(date_start, date_end):
            shows_by_day[day_of_year].append(on_this_day_show)
    return shows_by_day


def get_poster_items() -> list[schema.PosterItem]:
    """Every show with a primary image, in the archive's canonical show order."""
    return [
        schema.PosterItem(
            id=show_inst.id,
            title=show_inst.title,
            year_id=show_inst.year_id,
            year=show_inst.year,
            primary_image=assets.get_image_ref(show_inst.primary_image),
        )
        for show_inst in shows.get_show_query().where(
            database.Show.primary_image.is_null(False)
        )
    ]
