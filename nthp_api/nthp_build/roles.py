from typing import NamedTuple

import peewee
from slugify import slugify

from nthp_api.nthp_build import database, schema, years


class RoleDefinition(NamedTuple):
    name: str
    aliases: set[str] = set()


COMMITTEE_ROLE_DEFINITIONS: list[RoleDefinition] = [
    RoleDefinition(name="President"),
    RoleDefinition(name="Treasurer"),
]
CREW_ROLE_DEFINITIONS: list[RoleDefinition] = [
    RoleDefinition(name="Director"),
    RoleDefinition(name="Producer"),
    RoleDefinition(name="Musical Director"),
    RoleDefinition(
        name="Technical Director",
        aliases={
            "Tech Master",
        },
    ),
    RoleDefinition(
        name="Lighting Designer",
        aliases={
            "Lighting Design",
        },
    ),
    RoleDefinition(
        name="Sound Designer",
        aliases={
            "Sound Design",
        },
    ),
    RoleDefinition(
        name="Video Designer",
        aliases={
            "Video Design",
        },
    ),
    RoleDefinition(
        name="Composer",
        aliases={
            "Original Score",
        },
    ),
    RoleDefinition(name="Choreographer"),
    RoleDefinition(
        name="Make Up Artist",
        aliases={
            "Makeup Artist",
            "Makeup",
            "Make-Up",
            "Hair & Make-Up",
            "Hair & Makeup",
            "Hair & Makeup Artist",
        },
    ),
]

COMMITTEE_ROLE_DEFINITION_MAP = {r.name: r for r in COMMITTEE_ROLE_DEFINITIONS}
CREW_ROLE_DEFINITION_MAP = {r.name: r for r in CREW_ROLE_DEFINITIONS}

COMMITTEE_ROLES = [role.name for role in COMMITTEE_ROLE_DEFINITIONS]
CREW_ROLES = [role.name for role in CREW_ROLE_DEFINITIONS]


def get_role_id(role_name: str) -> str:
    return slugify(role_name, separator="_")


def _get_people_role_conditions(
    target_type: str,
) -> list[peewee.Expression]:
    return [
        database.PersonRole.target_type == target_type,
        database.PersonRole.person_id.is_null(False),
        database.PersonRole.person_name.is_null(False),
        database.PersonRole.is_person == True,  # noqa: E712, need to use ==
    ]


def get_people_committee_roles_by_role(
    role_name: str,
) -> list[schema.PersonCommitteeRoleList]:
    """
    Get a list of PersonCommitteeRoleList for a single role, will match aliases.
    People will be duplicated if they have held the position more than once.
    """
    role_names = {role_name} | COMMITTEE_ROLE_DEFINITION_MAP[role_name].aliases
    query = (
        database.PersonRole.select(database.PersonRole, database.Person)
        .where(
            database.PersonRole.role.in_(role_names),
            *_get_people_role_conditions(database.PersonRoleType.COMMITTEE),
        )
        .join(
            database.Person,
            on=(database.PersonRole.person_id == database.Person.id),
            attr="person",
            join_type=peewee.JOIN.LEFT_OUTER,
        )
    )
    return sorted(
        [
            schema.PersonCommitteeRoleList(
                id=r.person_id,
                title=r.person_name,
                headshot=r.person.headshot if getattr(r, "person", None) else None,
                year_title=years.get_year_title(
                    years.get_year_from_year_id(r.target_id)
                ),
                year_decade=years.get_year_decade(
                    years.get_year_from_year_id(r.target_id)
                ),
                year_id=r.target_id,
                role=r.role,
            )
            for r in query
        ],
        key=lambda person_committee_role_list: person_committee_role_list.year_title,
    )


def get_people_crew_roles_by_role(role_name: str) -> list[schema.PersonShowRoleList]:
    """
    Get a list of PersonShowRoleList for a single role, will match aliases.
    People will not duplicated.
    """
    role_names = {role_name} | CREW_ROLE_DEFINITION_MAP[role_name].aliases
    query = (
        database.PersonRole.select(
            database.PersonRole.person_id,
            database.PersonRole.person_name,
            database.Person.headshot,
            peewee.fn.count(database.PersonRole.person_id).alias("show_count"),
        )
        .where(
            database.PersonRole.role.in_(role_names),
            *_get_people_role_conditions(database.PersonRoleType.CREW),
        )
        .join(
            database.Person,
            on=(database.PersonRole.person_id == database.Person.id),
            attr="person",
            join_type=peewee.JOIN.LEFT_OUTER,
        )
        .group_by(
            database.PersonRole.person_id,
            database.PersonRole.person_name,
            database.Person.headshot,
        )
    )
    return sorted(
        [
            schema.PersonShowRoleList(
                id=r.person_id,
                title=r.person_name,
                headshot=r.person.headshot if getattr(r, "person", None) else None,
                role=role_name,
                show_count=r.show_count,
            )
            for r in query
        ],
        key=lambda person_show_role_list: person_show_role_list.id,
    )


def get_people_cast() -> list[schema.PersonShowRoleList]:
    """
    Get a list of PersonShowRoleList for acting.
    People will not duplicated.
    """
    query = (
        database.PersonRole.select(
            database.PersonRole.person_id,
            database.PersonRole.person_name,
            database.Person.headshot,
            peewee.fn.count(database.PersonRole.person_id).alias("show_count"),
        )
        .where(
            *_get_people_role_conditions(database.PersonRoleType.CAST),
        )
        .join(
            database.Person,
            on=(database.PersonRole.person_id == database.Person.id),
            attr="person",
            join_type=peewee.JOIN.LEFT_OUTER,
        )
        .group_by(
            database.PersonRole.person_id,
            database.PersonRole.person_name,
            database.Person.headshot,
        )
    )
    return sorted(
        [
            schema.PersonShowRoleList(
                id=r.person_id,
                title=r.person_name,
                headshot=r.person.headshot if getattr(r, "person", None) else None,
                role="Actor",
                show_count=r.show_count,
            )
            for r in query
        ],
        key=lambda person_show_role_list: person_show_role_list.id,
    )
