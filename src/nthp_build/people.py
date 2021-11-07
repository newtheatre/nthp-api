from typing import List, Optional, Iterable

import peewee
from slugify import slugify

import nthp_build.models
from nthp_build import database, schema


def get_person_id(name: str):
    return slugify(name, separator="_")


def save_person_roles(
    target: str,
    target_type: database.PersonRoleType,
    person_list: List[nthp_build.models.PersonRef],
):
    for person_ref in person_list:
        person_role = nthp_build.models.PersonRole(
            person_id=get_person_id(person_ref.name) if person_ref.name else None,
            person_name=person_ref.name,
            role=person_ref.role,
            note=person_ref.note,
            is_person=person_ref.person,
            comment=person_ref.comment,
        )
        database.PersonRole.create(
            target_id=target,
            target_type=target_type,
            person_id=person_role.person_id,
            person_name=person_role.person_name,
            role=person_role.role,
            is_person=person_role.is_person,
            data=person_role.json(),
        )

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
