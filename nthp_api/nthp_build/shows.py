import json
import logging
import re
from pathlib import Path

import peewee

from nthp_api.nthp_build import (
    assets,
    database,
    links,
    models,
    people,
    playwrights,
    schema,
    trivia,
    years,
)
from nthp_api.nthp_build.config import settings

log = logging.getLogger(__name__)

WRITER_SEPARATORS = re.compile(r",?\s+(?:and|&)\s+|,\s+")
NON_PERSON_PLAYWRIGHTS = {
    schema.PlaywrightType.VARIOUS.value,
    schema.PlaywrightType.UNKNOWN.value,
    "nnt creatives",
}


def get_show_query() -> peewee.Query:
    """
    Every show in the archive's canonical order.

    Year first: `season_sort` only orders shows within a year, so sorting on it
    across the archive would interleave the years. Within a year `season_sort` orders
    the shows that carry one, the rest falling to the end of the year as the old
    site's `_plugins/show.rb` `sort_shows` has them. `date_start` then orders shows
    that share a `season_sort`, and id breaks any remaining tie so the order is
    stable between builds.
    """
    return database.Show.select().order_by(
        database.Show.year,
        database.Show.season_sort.asc(nulls="LAST"),
        database.Show.date_start,
        database.Show.id,
    )


def get_show_play(show: models.Show) -> schema.PlayRef | None:
    """
    Decide if a show is a play or not and return a reference to it if it is.
    """
    if get_show_playwright(show) is not None:
        return schema.PlayRef(
            id=playwrights.get_play_id(show.title),
            title=show.title,
        )
    return None


def get_canonical_plays(
    show: models.Show, playwright_name: str
) -> list[tuple[str, str]]:
    """
    (play title, playwright name) pairs the show is indexed under.

    Each `canonical` entry yields one, falling back to the show's own title and
    playwright where it omits either; a show without any is indexed as itself.
    A student writing credit naming several people yields one pair per person,
    but a joint credit like `Gilbert & Sullivan` is left whole otherwise.
    """
    entries = show.canonical or [models.ShowCanonical()]
    return [
        (entry.title or show.title, writer)
        for entry in entries
        for writer in (
            split_writers(entry.playwright or playwright_name)
            if show.student_written
            else [entry.playwright or playwright_name]
        )
    ]


def get_show_playwright(  # noqa: PLR0911
    show: models.Show,
) -> schema.PlaywrightShow | None:
    if show.devised:
        if show.devised is True:
            return schema.PlaywrightShow(
                type=schema.PlaywrightType.DEVISED,
                name=None,
                descriptor="Devised",
                student_written=show.student_written,
            )
        if isinstance(show.devised, str):
            return schema.PlaywrightShow(
                type=schema.PlaywrightType.DEVISED,
                name=None,
                descriptor=f"Devised by {show.devised}",
                student_written=show.student_written,
            )
    if show.improvised is True:
        return schema.PlaywrightShow(
            type=schema.PlaywrightType.IMPROVISED,
            name=None,
            descriptor="Improvised",
            student_written=show.student_written,
        )
    if show.playwright is not None:
        if show.playwright.lower() == schema.PlaywrightType.VARIOUS.value:
            return schema.PlaywrightShow(
                type=schema.PlaywrightType.VARIOUS,
                name=None,
                descriptor="Various Writers",
                student_written=show.student_written,
            )
        if show.playwright.lower() == schema.PlaywrightType.UNKNOWN.value:
            return schema.PlaywrightShow(
                type=schema.PlaywrightType.UNKNOWN,
                name=None,
                descriptor="Unknown",
                student_written=show.student_written,
            )
        return schema.PlaywrightShow(
            type=schema.PlaywrightType.PLAYWRIGHT,
            id=playwrights.get_playwright_id(show.playwright),
            name=show.playwright,
            descriptor=f"by {show.playwright}",
            person_id=(
                people.get_person_id(show.playwright)
                if show.student_written
                and not has_multiple_writers(show.playwright)
                and show.playwright.lower() not in NON_PERSON_PLAYWRIGHTS
                else None
            ),
            student_written=show.student_written,
        )
    return None


def get_student_playwright_writers(show: models.Show) -> tuple[list[str], str] | None:
    """
    The student writers of a show and the role they take, or None where none do.

    In order of precedence the adaptor, translator or playwright is credited, under
    the student name `playwright_alias` gives where the writing was published under
    another name. A credit naming several people is split into one credit each, and
    `playwright_false` suppresses the credit outright.
    """
    if not show.student_written or show.playwright is None or show.playwright_false:
        return None
    if show.playwright.lower() in NON_PERSON_PLAYWRIGHTS:
        return None
    if show.adaptor is not None:
        writer, role = show.adaptor, "Adaptor"
    elif show.translator is not None:
        writer, role = show.translator, "Translator"
    else:
        writer, role = show.playwright, "Playwright"
    writers = split_writers(writer)
    if len(writers) == 1:
        writers = [show.playwright_alias or writer]
    return writers, role


def get_crew_with_student_playwright(
    show: models.Show, content_path: Path
) -> list[models.PersonRef]:
    """The crew list with the student writer credited at the top of it."""
    writers_role = get_student_playwright_writers(show)
    if writers_role is None:
        return show.crew
    writers, role = writers_role
    if any(person_ref.role == role for person_ref in show.crew):
        log.warning(f"{content_path}: credits its student {role.lower()} by hand")
        return show.crew
    return [
        *(models.PersonRef(role=role, name=writer) for writer in writers),
        *show.crew,
    ]


def has_multiple_writers(name: str) -> bool:
    return len(split_writers(name)) > 1


def split_writers(name: str) -> list[str]:
    """A writing credit's names, split apart on commas and conjunctions."""
    return [part.strip() for part in WRITER_SEPARATORS.split(name) if part.strip()]


def get_show_defects(show: models.Show) -> list[str]:
    """
    Authoring that the output silently drops, as reported at load time.

    Each defect costs the show a credit, a person page or an index entry, so each
    is worth fixing in the content repo.
    """
    defects = []
    if (show.devised or show.improvised) and show.playwright is not None:
        defects.append(
            f"playwright {show.playwright!r} is dropped, as the show is "
            f"{'devised' if show.devised else 'improvised'}"
        )
    writers_role = get_student_playwright_writers(show)
    if show.playwright_alias is not None and (
        writers_role is None or len(writers_role[0]) > 1
    ):
        defects.append(
            f"playwright_alias {show.playwright_alias!r} is inert, as the show "
            f"generates no sole student writing credit"
        )
    return defects


def get_show_date_defects(show: models.Show, year: int) -> list[str]:
    """Dates that contradict each other, or the academic year the show is filed in."""
    defects = []
    if (
        show.date_start is not None
        and show.date_end is not None
        and show.date_end.latest() < show.date_start.earliest()
    ):
        defects.append(
            f"date_end ({show.date_end}) is before date_start ({show.date_start})"
        )
    if show.date_start is not None and not years.check_date_in_year(
        show.date_start, year
    ):
        defects.append(
            f"date_start ({show.date_start}) is outside the academic year "
            f"{years.get_public_year_id(year)} it is filed under"
        )
    return defects


def get_show_roles(
    person_refs: list[models.PersonRef],
    headshots: dict[str, str | None] | None = None,
) -> list[schema.PersonCredit]:
    person_id_to_headshot = (
        headshots
        if headshots is not None
        else people.get_headshots_by_person_id(
            people.get_person_id(person_ref.name)
            for person_ref in person_refs
            if person_ref.name is not None
        )
    )
    show_roles = []
    for person_ref in person_refs:
        person_id = people.get_person_id(person_ref.name) if person_ref.name else None
        has_bio = person_id in person_id_to_headshot
        show_roles.append(
            schema.PersonCredit(
                role=person_ref.role,
                person=(
                    schema.PersonRef(
                        id=person_id,
                        title=person_ref.name,
                        is_person=person_ref.person,
                        headshot=assets.get_image_ref(
                            person_id_to_headshot.get(person_id)
                        ),
                        has_bio=has_bio,
                    )
                    if person_id
                    else None
                ),
                note=person_ref.note,
            )
        )
    return show_roles


def get_show_venue(
    show_inst: database.Show, show_data: models.Show
) -> schema.VenueRef | None:
    return (
        schema.VenueRef(
            id=show_inst.venue_id,
            name=show_data.venue,
        )
        if show_data.venue
        else None
    )


def get_show_missing_fields(
    show_inst: database.Show, show_data: models.Show
) -> list[schema.ShowMissingField]:
    """
    Facts the show record lacks, as the old site's `_plugins/show.rb` records them.

    How many missing facts make a record too thin to show is left to the consumer.
    """
    missing_fields = []
    if not show_inst.date_start:
        missing_fields.append(schema.ShowMissingField.DATE_START)
    if not show_inst.primary_image:
        missing_fields.append(schema.ShowMissingField.POSTER)
    if not show_inst.content:
        missing_fields.append(schema.ShowMissingField.EXCERPT)
    if not show_data.cast:
        missing_fields.append(schema.ShowMissingField.CAST)
    elif show_data.cast_incomplete:
        missing_fields.append(schema.ShowMissingField.CAST_INCOMPLETE)
    if not show_data.crew:
        missing_fields.append(schema.ShowMissingField.CREW)
    elif len(show_data.crew) <= settings.show_low_crew:
        missing_fields.append(schema.ShowMissingField.CREW_SHORT)
    playwright = get_show_playwright(show_data)
    if playwright is None or playwright.type == schema.PlaywrightType.UNKNOWN:
        # No authorship at all reads as unknown, as it does on the old site.
        missing_fields.append(schema.ShowMissingField.PLAYWRIGHT)
    if not show_data.venue:
        missing_fields.append(schema.ShowMissingField.VENUE)
    return missing_fields


def get_show_tour(show_data: models.Show) -> list[schema.ShowTourDate]:
    return [
        schema.ShowTourDate(
            venue=tour_date.venue,
            date_start=tour_date.date_start,
            date_end=tour_date.date_end,
            note=tour_date.note,
        )
        for tour_date in show_data.tour
    ]


def get_show_ref(show_inst: database.Show) -> schema.ShowRef:
    return schema.ShowRef(
        id=show_inst.id,
        title=show_inst.title,
        year_id=show_inst.year_id,
        year=show_inst.year,
        primary_image=assets.get_image_ref(show_inst.primary_image),
    )


def get_show_dated_ref(show_inst: database.Show) -> schema.ShowDatedRef:
    return schema.ShowDatedRef(
        **dict(get_show_ref(show_inst)),
        date_start=show_inst.date_start,
        date_end=show_inst.date_end,
    )


def get_show_index_item(show_inst: database.Show) -> schema.ShowIndexItem:
    source_data = models.Show(**json.loads(show_inst.data))
    playwright = get_show_playwright(source_data)
    return schema.ShowIndexItem(
        id=show_inst.id,
        title=show_inst.title,
        year_id=show_inst.year_id,
        year=show_inst.year,
        season=source_data.season,
        season_id=show_inst.season_id,
        venue=get_show_venue(show_inst, source_data),
        date_start=show_inst.date_start,
        date_end=show_inst.date_end,
        primary_image=assets.get_image_ref(show_inst.primary_image),
        playwright_descriptor=playwright.descriptor if playwright else None,
    )


def get_show_list_item(show_inst: database.Show) -> schema.ShowList:
    source_data = models.Show(**json.loads(show_inst.data))
    return schema.ShowList(
        **dict(get_show_index_item(show_inst)),
        playwright=get_show_playwright(source_data),
        adaptor=source_data.adaptor,
        devised=bool(source_data.devised),
    )


def get_show_detail(
    show_inst: database.Show,
    previous: schema.ShowRef | None = None,
    next_show: schema.ShowRef | None = None,
    headshots: dict[str, str | None] | None = None,
) -> schema.ShowDetail:
    """
    Build a show's detail. Pass every person's `headshots` when dumping many shows,
    to spare a lookup per show.
    """
    source_data = models.Show(**json.loads(show_inst.data))
    return schema.ShowDetail(
        **dict(get_show_list_item(show_inst)),
        play=get_show_play(source_data),
        translator=source_data.translator,
        company=source_data.company,
        period=source_data.period,
        tour=get_show_tour(source_data),
        cast=get_show_roles(source_data.cast, headshots),
        crew=get_show_roles(source_data.crew, headshots),
        cast_incomplete=source_data.cast_incomplete,
        cast_note=source_data.cast_note,
        crew_incomplete=source_data.crew_incomplete,
        crew_note=source_data.crew_note,
        # Even though we do have show assets in the db, fetching them for dumping per
        # show would be slow, so instead we use the saved result from when we loaded.
        assets=[
            assets.add_smugmug_image_info(schema.Asset(**asset))
            for asset in json.loads(show_inst.assets)
        ],
        links=links.get_links(source_data.links),
        missing_fields=get_show_missing_fields(show_inst, source_data),
        ignore_missing=source_data.ignore_missing,
        ignore_missing_in_seasons=(
            show_inst.season_id in settings.ignore_missing_in_season_ids
        ),
        previous=previous,
        next=next_show,
        trivia=trivia.make_target_trivia(
            show_inst.id, database.TargetType.SHOW, headshots
        ),
        content=show_inst.content,
    )


def get_show_people_names(show: schema.ShowDetail) -> list[str]:
    return sorted(
        {
            credit.person.title
            for credit in [*show.cast, *show.crew]
            if credit.person is not None
        }
    )
