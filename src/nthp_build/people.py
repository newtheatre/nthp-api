from typing import List

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
