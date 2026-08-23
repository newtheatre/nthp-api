import json
import logging
from typing import NamedTuple

import peewee
from slugify import slugify

from nthp_api.nthp_build import assets, database, models, schema

log = logging.getLogger(__name__)

UNKNOWN_ROLE_NAMES = {"unknown", "Unknown"}

CAST_ROLE_NAME = "Actor"


class RoleDefinition(NamedTuple):
    name: str
    aliases: set[str] = set()  # noqa: RUF012


COMMITTEE_ROLE_ALIASES: dict[str, set[str]] = {
    "Committee Member": {"Committee Members"},
    "Costume, Props and Make-Up Manager": {
        "Costume, Props and Make-up Manager",
        "Costume, Props and Makeup Manager",
    },
    "Front of House Manager": {"Front of House", "House Manager"},
    "Health and Safety Officer": {"Safety Officer"},
    "Marketing Coordinator": {"Marketing Co-ordinator"},
    "Production Manager": {"Productions Manager"},
    "Publicity and External Marketing Manager": {"Publicity and External Marketing"},
    "Publicity and Internal Marketing Manager": {"Publicity and Internal Marketing"},
}

COMMITTEE_ROLE_CANONICAL_NAMES: dict[str, str] = {
    alias: name for name, aliases in COMMITTEE_ROLE_ALIASES.items() for alias in aliases
}


def get_role_id(role_name: str) -> str:
    return slugify(role_name, separator="_")


def save_crew_role_definitions(
    definitions: models.CrewRoleDefinitionCollection,
) -> None:
    database.CrewRoleDefinition.insert_many(
        [
            {
                "name": definition.role,
                "sort": sort,
                "aliases": json.dumps(definition.aliases),
            }
            for sort, definition in enumerate(definitions)
        ]
    ).execute()


def get_crew_role_definitions() -> list[RoleDefinition]:
    """Crew roles as defined by the content repo, in the order defined there."""
    return [
        RoleDefinition(name=inst.name, aliases=set(json.loads(inst.aliases)))
        for inst in database.CrewRoleDefinition.select().order_by(
            database.CrewRoleDefinition.sort
        )
    ]


def get_distinct_role_names(target_type: str) -> list[str]:
    query = (
        database.PersonRole.select(database.PersonRole.role)
        .where(
            database.PersonRole.role.is_null(False),
            database.PersonRole.target_type == target_type,
        )
        .distinct()
    )
    return sorted(database.not_null(inst.role) for inst in query)


def get_committee_role_definitions() -> list[RoleDefinition]:
    """
    Committee roles as held in the content, near-duplicates folded together.

    Unlike crew roles, committee roles have no content-side definition, so the role
    set is whatever has been authored, with the curated alias map layered on top.
    """
    names = {
        COMMITTEE_ROLE_CANONICAL_NAMES.get(role_name, role_name)
        for role_name in get_distinct_role_names(database.PersonRoleType.COMMITTEE)
        if role_name not in UNKNOWN_ROLE_NAMES
    }
    return [
        RoleDefinition(name=name, aliases=COMMITTEE_ROLE_ALIASES.get(name, set()))
        for name in sorted(names)
    ]


def get_crew_roles_without_definition() -> list[str]:
    """Crew roles authored in the content that no definition in roles.yaml covers."""
    defined_names = {
        role_name
        for definition in get_crew_role_definitions()
        for role_name in {definition.name} | definition.aliases
    }
    return [
        role_name
        for role_name in get_distinct_role_names(database.PersonRoleType.CREW)
        if role_name not in defined_names
    ]


def _get_people_role_conditions(
    target_type: str,
) -> list[peewee.Expression]:
    return [
        database.PersonRole.target_type == target_type,
        database.PersonRole.person_id.is_null(False),
        database.PersonRole.person_name.is_null(False),
        database.PersonRole.is_person == True,  # noqa: E712, need to use ==
    ]


def get_role_names(definition: RoleDefinition) -> set[str]:
    return {definition.name} | definition.aliases


def get_crew_role_canonical_names() -> dict[str, str]:
    """Every defined crew role name and alias against the canonical name for it."""
    return {
        role_name: definition.name
        for definition in get_crew_role_definitions()
        for role_name in get_role_names(definition)
    }


def get_role_holding_count(definition: RoleDefinition, target_type: str) -> int:
    """How many times the role, aliases included, has been held."""
    return (
        database.PersonRole.select()
        .where(
            database.PersonRole.role.in_(get_role_names(definition)),
            *_get_people_role_conditions(target_type),
        )
        .count()
    )


def get_role_list(definition: RoleDefinition, target_type: str) -> schema.Role:
    return schema.Role(
        id=get_role_id(definition.name),
        name=definition.name,
        aliases=sorted(definition.aliases),
        holding_count=get_role_holding_count(definition, target_type),
    )


def get_person_ref(row: database.PersonRole) -> schema.PersonRef:
    """The person a role row credits, with the bio the outer join found for them."""
    person = getattr(row, "person", None)
    headshot = person.headshot if person is not None and person.id is not None else None
    return schema.PersonRef(
        id=row.person_id,
        title=row.person_name,
        is_person=True,
        has_bio=person is not None and person.id is not None,
        headshot=assets.get_image_ref(headshot),
    )


def get_people_committee_roles_by_role(
    definition: RoleDefinition,
) -> list[schema.PersonCommitteeRoleList]:
    """
    Get a list of PersonCommitteeRoleList for a single role, will match aliases.
    People will be duplicated if they have held the position more than once.
    """
    query = (
        database.PersonRole.select(database.PersonRole, database.Person)
        .where(
            database.PersonRole.role.in_(get_role_names(definition)),
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
                person=get_person_ref(r),
                year=schema.YearRef.from_start_year(r.target_year),
                role=r.role,
            )
            for r in query
        ],
        key=lambda person_committee_role_list: person_committee_role_list.year.id,
    )


def get_people_crew_roles_by_role(
    definition: RoleDefinition,
) -> list[schema.PersonShowRoleList]:
    """
    Get a list of PersonShowRoleList for a single role, will match aliases.
    People will not duplicated.
    """
    query = (
        database.PersonRole.select(
            database.PersonRole.person_id,
            database.PersonRole.person_name,
            database.Person.id,
            database.Person.headshot,
            peewee.fn.count(database.PersonRole.person_id).alias("show_count"),
        )
        .where(
            database.PersonRole.role.in_(get_role_names(definition)),
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
            database.Person.id,
            database.Person.headshot,
        )
    )
    return sorted(
        [
            schema.PersonShowRoleList(
                person=get_person_ref(r),
                role=definition.name,
                show_count=r.show_count,  # type: ignore[attr-defined]
            )
            for r in query
        ],
        key=lambda person_show_role_list: person_show_role_list.person.id,
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
            database.Person.id,
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
            database.Person.id,
            database.Person.headshot,
        )
    )
    return sorted(
        [
            schema.PersonShowRoleList(
                person=get_person_ref(r),
                role=CAST_ROLE_NAME,
                show_count=r.show_count,  # type: ignore[attr-defined]
            )
            for r in query
        ],
        key=lambda person_show_role_list: person_show_role_list.person.id,
    )
