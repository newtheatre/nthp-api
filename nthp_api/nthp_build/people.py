import datetime
import json
import logging
from collections import defaultdict
from collections.abc import Iterable
from typing import Any, cast

import peewee
from slugify import slugify

from nthp_api.nthp_build import assets, database, links, models, schema
from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.fields import FuzzyDate

log = logging.getLogger(__name__)

SHOW_ROLE_TYPES = [database.PersonRoleType.CAST, database.PersonRoleType.CREW]

SHOW_ROLE_TYPES_TO_SCHEMA = {
    database.PersonRoleType.CAST: schema.ShowRoleType.CAST,
    database.PersonRoleType.CREW: schema.ShowRoleType.CREW,
}


def get_person_id(name: str) -> str:
    return slugify(name, separator="_")


def save_person_roles(
    target: str,  # TODO: should be target_id
    target_type: str,  # TODO: why not PersonRoleType?
    target_year: int,
    person_list: list[models.PersonRef],
) -> list[models.PersonRole]:
    rows = []
    person_roles: list[models.PersonRole] = []
    for person_ref in person_list:
        person_role = models.PersonRole(
            person_id=get_person_id(person_ref.name) if person_ref.name else None,
            person_name=person_ref.name,
            role=person_ref.role,
            note=person_ref.note,
            is_person=person_ref.person,
            comment=person_ref.comment,
        )
        person_roles.append(person_role)
        rows.append(
            {
                "target_id": target,
                "target_type": target_type,
                "target_year": target_year,
                "person_id": person_role.person_id,
                "person_name": person_role.person_name,
                "role": person_role.role,
                "is_person": person_role.is_person,
                "data": person_role.model_dump_json(),
            }
        )
    database.PersonRole.insert_many(rows).execute()
    return person_roles


def get_real_people() -> "peewee.ModelSelect[database.Person]":
    return database.Person.select()


def get_headshots_by_person_id(person_ids: Iterable[str]) -> dict[str, str | None]:
    """Headshot of each person the archive holds a document for, by id."""
    query = database.Person.select(database.Person.id, database.Person.headshot).where(
        database.Person.id.in_(list(person_ids))
    )
    return {person.id: person.headshot for person in query}


def make_person_credits(
    person_roles: Iterable[models.PersonRole],
) -> list[schema.PersonCredit]:
    """Credits as a document shows them, with each person's bio and headshot."""
    person_roles = list(person_roles)
    headshots = get_headshots_by_person_id(
        person_role.person_id
        for person_role in person_roles
        if person_role.person_id is not None
    )
    return [
        schema.PersonCredit(
            role=person_role.role,
            person=(
                schema.PersonRef(
                    id=person_role.person_id,
                    title=person_role.person_name,
                    is_person=person_role.is_person,
                    has_bio=person_role.person_id in headshots,
                    headshot=assets.get_image_ref(headshots.get(person_role.person_id)),
                )
                if person_role.person_id and person_role.person_name
                else None
            ),
            note=person_role.note,
        )
        for person_role in person_roles
    ]


def get_person_show_roles(person_id: str) -> list[schema.PersonShowRoles]:
    query = (
        database.PersonRole.select(database.PersonRole, database.Show)
        .where(
            database.PersonRole.person_id == person_id,
            database.PersonRole.target_type.in_(SHOW_ROLE_TYPES),
        )
        .join(
            database.Show,
            on=(database.PersonRole.target_id == database.Show.id),
            attr="show",
        )
        .order_by(database.Show.year_id, database.Show.season_sort)
    )
    # Collect all results by show_id
    results_by_show_id: dict[str, list] = defaultdict(list)
    shows: dict[str, database.Show] = {}
    for result in query:
        results_by_show_id[result.target_id].append(result)
        shows[result.target_id] = result.show  # type: ignore[attr-defined]

    return [
        schema.PersonShowRoles(
            show=schema.ShowRef(
                id=show_id,
                title=shows[show_id].title,
                year_id=shows[show_id].year_id,
                year=shows[show_id].year,
                primary_image=assets.get_image_ref(shows[show_id].primary_image),
            ),
            roles=[
                schema.PersonShowRoleItem(
                    role=role.role,
                    role_type=SHOW_ROLE_TYPES_TO_SCHEMA[role.target_type],
                )
                for role in roles
            ],
        )
        for show_id, roles in results_by_show_id.items()
    ]


def get_person_committee_roles(person_id: str) -> list[schema.PersonCommitteeRole]:
    query = database.PersonRole.select().where(
        database.PersonRole.person_id == person_id,
        database.PersonRole.target_type == database.PersonRoleType.COMMITTEE,
    )

    return [
        schema.PersonCommitteeRole(
            year=schema.YearRef.from_start_year(person_role.target_year),
            role=person_role.role,
        )
        for person_role in query
    ]


def _role_count_map(query: "peewee.ModelSelect[Any]") -> dict[str, int]:
    rows = cast("Iterable[dict[str, Any]]", query.dicts())
    return {row["person_id"]: row["role_count"] for row in rows}


def get_show_role_counts() -> dict[str, int]:
    """
    Count shows worked on, per person, in a single query.

    Counts distinct shows rather than role rows, as `get_person_show_roles` groups
    a person's roles by show.
    """
    query = (
        database.PersonRole.select(
            database.PersonRole.person_id,
            peewee.fn.COUNT(peewee.fn.DISTINCT(database.PersonRole.target_id)).alias(
                "role_count"
            ),
        )
        .where(
            database.PersonRole.person_id.is_null(False),
            database.PersonRole.target_type.in_(SHOW_ROLE_TYPES),
        )
        .group_by(database.PersonRole.person_id)
    )
    return _role_count_map(query)


def get_committee_role_counts() -> dict[str, int]:
    """
    Count committee positions held, per person, in a single query.

    Counts role rows, as `get_person_committee_roles` emits one entry per row: a
    person holding the same position twice holds it twice.
    """
    query = (
        database.PersonRole.select(
            database.PersonRole.person_id,
            peewee.fn.COUNT(database.PersonRole.person_id).alias("role_count"),
        )
        .where(
            database.PersonRole.person_id.is_null(False),
            database.PersonRole.target_type == database.PersonRoleType.COMMITTEE,
        )
        .group_by(database.PersonRole.person_id)
    )
    return _role_count_map(query)


def get_person_collaborators(person_id: str) -> list[schema.PersonCollaborator]:
    """
    Get all collaborators for a person. A collaborator is a person who has worked on a
    show or other object (such as committee) with the source person.
    :param person_id: Which person to get collaborators for
    :return: A set of collaborators
    """
    # Get a list of targets to look for collaborators, shows where person_id is present
    target_query = database.PersonRole.select(
        database.PersonRole.target_id.distinct()
    ).where(database.PersonRole.person_id == person_id)
    targets = [target.target_id for target in target_query]
    # Find all collaborators
    collaborator_roles_query = (
        database.PersonRole.select()
        .where(
            database.PersonRole.target_id.in_(
                targets
            ),  # show where person_id is present
            database.PersonRole.person_id != person_id,  # exclude source person
            database.PersonRole.person_id.is_null(False),  # exclude null person_id
            database.PersonRole.is_person == True,  # noqa: E712, need to use ==
        )
        .order_by(database.PersonRole.person_id)
    )
    # Map collaborators against a list of targets
    collaborator_map: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for collaborator_role in collaborator_roles_query:
        if collaborator_role.person_id is None or collaborator_role.person_name is None:
            continue
        collaborator_map[
            (collaborator_role.person_id, collaborator_role.person_name)
        ].add(collaborator_role.target_id)
    # Return a set of collaborators
    headshots = get_headshots_by_person_id(
        collaborator_id for collaborator_id, _ in collaborator_map
    )
    return [
        schema.PersonCollaborator(
            person=schema.PersonRef(
                id=collaborator_id,
                title=collaborator_name,
                is_person=True,
                has_bio=collaborator_id in headshots,
                headshot=assets.get_image_ref(headshots.get(collaborator_id)),
            ),
            target_ids=sorted(target_ids),
        )
        for (collaborator_id, collaborator_name), target_ids in collaborator_map.items()
    ]


def get_people_from_roles(
    excluded_ids: Iterable[str] | None = None,
) -> "peewee.ModelSelect[database.PersonRole]":
    """
    Get people from person roles, optionally excluding a list of person ids.
    """
    return (
        database.PersonRole.select(
            database.PersonRole.person_id, database.PersonRole.person_name
        )
        .where(database.PersonRole.person_id.not_in(excluded_ids or []))
        .where(database.PersonRole.person_id.is_null(False))
        .where(database.PersonRole.is_person == True)  # noqa: E712, need to use ==
        .group_by(database.PersonRole.person_id)
        .order_by(database.PersonRole.person_id)
    )


def get_graduation(model: models.Person) -> schema.PersonGraduated | None:
    """
    Either get a PersonGraduated from the provided year for the person, or make an
    estimate based on their credits.
    """
    if model.graduated:
        return schema.PersonGraduated.from_grad_year(model.graduated, estimated=False)

    years_active_query = database.PersonRole.select(
        database.PersonRole.target_year.distinct()
    ).where(database.PersonRole.person_id == model.id)
    years_active = [year.target_year for year in years_active_query]
    last_year_active = max(years_active) if years_active else None

    if last_year_active:
        how_many_years_ago_was_that = datetime.date.today().year - last_year_active
        # Only use the estimate if a certain amount of time has passed.
        if how_many_years_ago_was_that > settings.graduation_recency_limit or (
            how_many_years_ago_was_that == settings.graduation_recency_limit
            and datetime.date.today().month >= settings.graduation_month
        ):
            return schema.PersonGraduated.from_grad_year(
                last_year_active + 1,  # Add one as active in 1999-00 is grad in 2000
                estimated=True,
            )

    # Probably not graduated
    return None


def get_is_student(
    graduation: schema.PersonGraduated | None, *, has_credits: bool
) -> bool:
    """
    Whether the person is likely still a student, as of the build date.

    Those yet to graduate, and those graduating later this year, are students, as
    the old site's `_plugins/people.rb` has it. Someone with no credits at all is
    nobody's student. Estimated graduations are only made once the recency limit
    has passed, so they always read as graduated.
    """
    if not has_credits:
        return False
    if graduation is None:
        return True
    today = datetime.date.today()
    return graduation.grad_year > today.year or (
        graduation.grad_year == today.year and today.month < settings.graduation_month
    )


def get_person_sort_key(title: str) -> tuple[str, str]:
    """Surname then forename, as the old site's `sort_people` orders people."""
    names = title.split()
    return (names[-1] if names else title, " ".join(names[:-1]))


def get_award_holders() -> dict[str, dict[str, list[schema.PersonRef]]]:
    """
    People who received an award, by the academic year they graduated in.

    Awards belong to the year the person graduated in, estimates included, as the
    old site's `_plugins/awards.rb` files them. Anyone whose graduation is unknown
    has nowhere to be filed.
    """
    holders: dict[str, dict[str, list[schema.PersonRef]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for person_inst in get_real_people():
        model = models.Person(**json.loads(person_inst.data))
        if model.award is None:
            continue
        graduation = get_graduation(model)
        if graduation is None:
            # Reported by the post-load `award graduation` check, which knows the
            # document the award was authored in.
            continue
        holders[graduation.id][model.award].append(
            schema.PersonRef(
                id=person_inst.id,
                title=model.title,
                is_person=True,
                has_bio=True,
                headshot=assets.get_image_ref(person_inst.headshot),
            )
        )
    return {
        year_id: {
            award: sorted(people, key=lambda person: get_person_sort_key(person.title))
            for award, people in awards.items()
        }
        for year_id, awards in holders.items()
    }


def make_virtual_person_model(ref) -> models.Person:
    """Make a Person model not from a file but from cast/crew lists"""
    return models.Person(
        id=ref.person_id,
        title=ref.person_name,
    )


def get_submission(
    submitted: FuzzyDate | bool | None,
) -> tuple[bool, FuzzyDate | None]:
    """
    Whether the person submitted the record, and when, from the authored value.

    Records are authored with either a submission date or a bare boolean, so a date
    means submitted and a boolean carries no date.
    """
    if isinstance(submitted, FuzzyDate):
        return True, submitted
    return bool(submitted), None


def make_person_detail(
    model: models.Person,
    content: str | None = None,
    trivia: list[schema.Trivia] | None = None,
    *,
    has_bio: bool,
) -> schema.PersonDetail:
    assert model.id is not None, "Person model should have id by now"
    graduation = get_graduation(model)
    show_roles = get_person_show_roles(model.id)
    committee_roles = get_person_committee_roles(model.id)
    submitted, submitted_date = get_submission(model.submitted)
    return schema.PersonDetail(
        id=model.id,
        title=model.title,
        has_bio=has_bio,
        submitted=submitted,
        submitted_date=submitted_date,
        headshot=(
            assets.asset_from_headshot(model.headshot) if model.headshot else None
        ),
        graduated=graduation,
        show_roles=show_roles,
        committee_roles=committee_roles,
        show_role_count=len(show_roles),
        committee_role_count=len(committee_roles),
        course=model.course,
        award=model.award,
        careers=model.careers,
        student=get_is_student(
            graduation, has_credits=bool(show_roles or committee_roles)
        ),
        links=links.get_links(model.links),
        news=links.get_links(model.news),
        trivia=trivia or [],
        content=content,
    )
