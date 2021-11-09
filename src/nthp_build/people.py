from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

import peewee
from slugify import slugify

import nthp_build.models
from nthp_build import database, schema, years


def get_person_id(name: str) -> str:
    return slugify(name, separator="_")


def save_person_roles(
    target: str,
    target_type: database.PersonRoleType,
    person_list: List[nthp_build.models.PersonRef],
):
    rows = []
    for person_ref in person_list:
        person_role = nthp_build.models.PersonRole(
            person_id=get_person_id(person_ref.name) if person_ref.name else None,
            person_name=person_ref.name,
            role=person_ref.role,
            note=person_ref.note,
            is_person=person_ref.person,
            comment=person_ref.comment,
        )
        rows.append(
            {
                "target_id": target,
                "target_type": target_type,
                "person_id": person_role.person_id,
                "person_name": person_role.person_name,
                "role": person_role.role,
                "is_person": person_role.is_person,
                "data": person_role.json(),
            }
        )
    database.PersonRole.insert_many(rows).execute()


def get_real_people() -> peewee.ModelSelect:
    return database.Person.select()


def get_person_show_roles(person_id: str) -> List[schema.PersonShowRoles]:
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
    results_by_show_id: Dict[str, List] = defaultdict(list)
    shows: Dict[str, Any] = defaultdict(list)
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


def get_person_committee_roles(person_id: str) -> List[schema.PersonCommitteeRole]:
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


def get_people_from_roles(
    excluded_ids: Optional[Iterable[str]] = None,
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
        .where(database.PersonRole.is_person == True)
        .group_by(database.PersonRole.person_id)
    )
