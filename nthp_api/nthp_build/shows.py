import json
import logging
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

MULTIPLE_WRITER_SEPARATORS = (" and ", ", ", " & ")
NON_PERSON_PLAYWRIGHTS = {
    schema.PlaywrightType.VARIOUS.value,
    schema.PlaywrightType.UNKNOWN.value,
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
                people.get_person_id(show.playwright) if show.student_written else None
            ),
            student_written=show.student_written,
        )
    return None


def get_student_playwright_credit(show: models.Show) -> models.PersonRef | None:
    """
    The crew credit a student writer takes, as `_plugins/show.rb` awards it.

    In order of precedence the adaptor, translator or playwright is credited, under
    the student name `playwright_alias` gives where the writing was published under
    another name. Shows written by several people are skipped, as the names cannot
    be split apart reliably, and `playwright_false` suppresses the credit outright.
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
    if has_multiple_writers(writer):
        return None
    return models.PersonRef(role=role, name=show.playwright_alias or writer)


def get_crew_with_student_playwright(
    show: models.Show, content_path: Path
) -> list[models.PersonRef]:
    """The crew list with the student writer credited at the top of it."""
    credit = get_student_playwright_credit(show)
    if credit is None:
        return show.crew
    if any(person_ref.role == credit.role for person_ref in show.crew):
        log.warning(
            f"{content_path}: credits its student {credit.role.lower()} by hand"
        )
        return show.crew
    return [credit, *show.crew]


def has_multiple_writers(name: str) -> bool:
    return any(separator in name for separator in MULTIPLE_WRITER_SEPARATORS)


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
    if (
        show.student_written
        and show.playwright is not None
        and has_multiple_writers(show.playwright)
    ):
        defects.append(
            f"student writer {show.playwright!r} names several people, so none of "
            f"them takes a crew credit or a person page"
        )
    if (
        show.playwright_alias is not None
        and get_student_playwright_credit(show) is None
    ):
        defects.append(
            f"playwright_alias {show.playwright_alias!r} is inert, as the show "
            f"generates no student writing credit"
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


def get_show_roles(person_refs: list[models.PersonRef]) -> list[schema.PersonCredit]:
    query = database.Person.select(database.Person.id, database.Person.headshot).where(
        database.Person.id.in_(
            [
                people.get_person_id(person_ref.name)
                for person_ref in person_refs
                if person_ref.name is not None
            ]
        )
    )
    person_id_to_headshot = {r.id: r.headshot for r in query}
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
) -> schema.ShowDetail:
    source_data = models.Show(**json.loads(show_inst.data))
    return schema.ShowDetail(
        **dict(get_show_list_item(show_inst)),
        play=get_show_play(source_data),
        translator=source_data.translator,
        company=source_data.company,
        period=source_data.period,
        tour=get_show_tour(source_data),
        cast=get_show_roles(source_data.cast),
        crew=get_show_roles(source_data.crew),
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
        trivia=trivia.make_target_trivia(show_inst.id, database.TargetType.SHOW),
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
