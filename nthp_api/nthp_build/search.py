"""Building the search corpus, one faceted document per record the site indexes."""

from nthp_api.nthp_build import database, roles, schema, shows, venues, years
from nthp_api.nthp_build.parallel import DumperSharedState


def add_document(state: DumperSharedState, document: schema.SearchDocument) -> None:
    state.search_documents.append(document)


def get_show_document(
    show_inst: database.Show, show: schema.ShowDetail
) -> schema.SearchDocumentShow:
    return schema.SearchDocumentShow(
        type=schema.SearchDocumentType.SHOW,
        title=show.title,
        id=show.id,
        image_id=show_inst.primary_image,
        year_id=show_inst.year_id,
        year=show_inst.year,
        decade=years.get_year_decade(show_inst.year),
        season=show.season,
        season_id=show.season_id,
        venue_id=show.venue.id if show.venue else None,
        venue_name=show.venue.name if show.venue else None,
        date_start=show.date_start,
        playwright=show.playwright.descriptor if show.playwright else None,
        company=show.company,
        people=shows.get_show_people_names(show) or None,
        plaintext=show_inst.plaintext,
    )


def get_person_show_role_names(
    person: schema.PersonDetail, crew_role_canonical_names: dict[str, str]
) -> list[str]:
    """
    Distinct roles the person has taken on a show, under their canonical names.

    Acting is a single role however the part was named, matching the `/roles/cast`
    index; crew roles fold their aliases together, and roles the content repo's
    `roles.yaml` does not define pass through as authored.
    """
    role_names = set()
    for show_roles in person.show_roles:
        for show_role in show_roles.roles:
            if show_role.role_type == database.PersonRoleType.CAST:
                role_names.add(roles.CAST_ROLE_NAME)
            elif (
                show_role.role is not None
                and show_role.role not in roles.UNKNOWN_ROLE_NAMES
            ):
                role_names.add(
                    crew_role_canonical_names.get(show_role.role, show_role.role)
                )
    return sorted(role_names)


def get_person_committee_role_names(person: schema.PersonDetail) -> list[str]:
    """Distinct committee positions the person has held, under their canonical names."""
    return sorted(
        {
            roles.COMMITTEE_ROLE_CANONICAL_NAMES.get(role.role, role.role)
            for role in person.committee_roles
            if role.role not in roles.UNKNOWN_ROLE_NAMES
        }
    )


def get_person_year_ids(person: schema.PersonDetail) -> list[str]:
    """Academic years the person is credited in, on a show or a committee."""
    return sorted(
        {show_roles.show_year_id for show_roles in person.show_roles}
        | {role.year_id for role in person.committee_roles}
    )


def get_person_document(
    person: schema.PersonDetail,
    crew_role_canonical_names: dict[str, str],
    *,
    has_bio: bool,
    plaintext: str | None = None,
) -> schema.SearchDocumentPerson:
    graduated = person.graduated
    return schema.SearchDocumentPerson(
        type=schema.SearchDocumentType.PERSON,
        title=person.title,
        id=person.id,
        image_id=person.headshot.id if person.headshot else None,
        has_bio=has_bio,
        graduation_year=graduated.year_id if graduated else None,
        graduation_decade=graduated.year_decade if graduated else None,
        graduation_estimated=graduated.estimated if graduated else None,
        course=person.course or None,
        careers=person.careers or None,
        award=person.award,
        show_roles=get_person_show_role_names(person, crew_role_canonical_names)
        or None,
        committee_roles=get_person_committee_role_names(person) or None,
        show_count=len(person.show_roles),
        year_ids=get_person_year_ids(person) or None,
        plaintext=plaintext,
    )


def get_venue_document(record: venues.VenueRecord) -> schema.SearchDocumentVenue:
    return schema.SearchDocumentVenue(
        type=schema.SearchDocumentType.VENUE,
        title=record.name,
        id=record.id,
        city=record.document_data.city if record.document_data else None,
        show_count=len(record.shows),
        plaintext=record.document.plaintext if record.document else None,
    )


def get_year_document(year: schema.YearDetail) -> schema.SearchDocumentYear:
    return schema.SearchDocumentYear(
        type=schema.SearchDocumentType.YEAR,
        title=year.title,
        id=year.year_id,
        decade=year.decade,
        show_count=year.show_count,
    )
