import datetime
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import peewee
from slugify import slugify

from nthp_api.nthp_build import database, models, schema, years
from nthp_api.nthp_build.config import settings


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
                "data": person_role.json(),
            }
        )
    database.PersonRole.insert_many(rows).execute()
    return person_roles


def get_real_people() -> peewee.ModelSelect:
    return database.Person.select()


def get_person_show_roles(person_id: str) -> list[schema.PersonShowRoles]:
    query = (
        database.PersonRole.select(database.PersonRole, database.Show)
        .where(
            database.PersonRole.person_id == person_id,
            database.PersonRole.target_type.in_(
                [database.PersonRoleType.CAST, database.PersonRoleType.CREW]
            ),
        )
        .join(
            database.Show,
            on=(database.PersonRole.target_id == database.Show.id),
            attr="show",
        )
    )
    # Collect all results by show_id
    results_by_show_id: dict[str, list] = defaultdict(list)
    shows: dict[str, Any] = defaultdict(list)
    for result in query:
        results_by_show_id[result.target_id].append(result)
        shows[result.target_id] = result.show

    return [
        schema.PersonShowRoles(
            show_id=show_id,
            show_title=shows[show_id].title,
            roles=[
                schema.PersonShowRoleItem(role=role.role, role_type=role.target_type)
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
            year_id=person_role.target_id,
            year_title=years.get_year_title(
                years.get_year_from_year_id(person_role.target_id)
            ),
            year_decade=years.get_year_decade(
                years.get_year_from_year_id(person_role.target_id)
            ),
            role=person_role.role,
        )
        for person_role in query
    ]


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
    collaborator_map = defaultdict(set)
    for collaborator_role in collaborator_roles_query:
        collaborator_map[
            (collaborator_role.person_id, collaborator_role.person_name)
        ].add(collaborator_role.target_id)
    # Return a set of collaborators
    return [
        schema.PersonCollaborator(
            person_id=person_id,
            person_name=person_name,
            target_ids=sorted(target_ids),
        )
        for (person_id, person_name), target_ids in collaborator_map.items()
    ]


def get_people_from_roles(
    excluded_ids: Iterable[str] | None = None,
) -> peewee.ModelSelect:
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
        return schema.PersonGraduated.from_year(model.graduated, estimated=False)

    years_active_query = database.PersonRole.select(
        database.PersonRole.target_year.distinct()
    ).where(database.PersonRole.person_id == model.id)
    years_active = [year.target_year for year in years_active_query]
    last_year_active = max(years_active) if years_active else None

    if last_year_active:
        how_many_years_ago_was_that = datetime.date.today().year - last_year_active
        # Only use the estimate if a certain amount of time has passed.
        if (
            how_many_years_ago_was_that > settings.graduation_recency_limit
            or how_many_years_ago_was_that == settings.graduation_recency_limit
            and datetime.date.today().month >= settings.graduation_month
        ):
            return schema.PersonGraduated.from_year(
                last_year_active + 1,  # Add one as active in 1999-00 is grad in 2000
                estimated=True,
            )

    # Probably not graduated
    return None


def make_virtual_person_model(ref) -> models.Person:
    """Make a Person model not from a file but from cast/crew lists"""
    return models.Person(
        id=ref.person_id,
        title=ref.person_name,
    )


def make_person_detail(
    model: models.Person,
    content: str | None = None,
) -> schema.PersonDetail:
    assert model.id is not None, "Person model should have id by now"
    return schema.PersonDetail(
        id=model.id,
        title=model.title,
        submitted=model.submitted,
        headshot=model.headshot,
        graduated=get_graduation(model),
        show_roles=get_person_show_roles(model.id),
        committee_roles=get_person_committee_roles(model.id),
        content=content,
    )
