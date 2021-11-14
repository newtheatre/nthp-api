import contextlib
import datetime
import json
import logging
import shutil
import time
from pathlib import Path
from typing import List

import pydantic

from nthp_build import (
    database,
    people,
    playwrights,
    roles,
    schema,
    search,
    shows,
    spec,
    years,
)
from nthp_build.config import settings

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("dist")


def delete_output_dir():
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def make_out_path(directory: Path, file: str) -> Path:
    path = OUTPUT_DIR / directory / Path(file + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_file(path: Path, obj: pydantic.BaseModel) -> None:
    with open(path, "w") as f:
        f.write(obj.json(by_alias=True))


def dump_show(inst: database.Show) -> schema.ShowDetail:
    path = make_out_path(Path("shows"), inst.id)
    show = shows.get_show_detail(inst)
    search.add_document(
        type=schema.SearchDocumentType.SHOW,
        title=show.title,
        id=inst.id,
        playwright=show.playwright,
        company=show.company,
        people=shows.get_show_people_names(show),
        plaintext=inst.plaintext,
    )
    write_file(path, show)
    return show


def dump_year(year: int) -> schema.YearDetail:
    year_id = years.get_year_id(year)
    path = make_out_path(Path("years"), year_id)
    year_shows = shows.get_show_query().where(database.Show.year_id == year_id)
    year_committee = database.PersonRole.select().where(
        database.PersonRole.target_type == database.PersonRoleType.COMMITTEE,
        database.PersonRole.target_id == year_id,
    )
    year_detail = schema.YearDetail(
        title=years.get_year_title(year),
        decade=years.get_year_decade(year),
        year_id=year_id,
        start_year=year,
        grad_year=year + 1,
        show_count=len(year_shows),
        shows=[shows.get_show_list_item(show_inst) for show_inst in year_shows],
        committee=[
            schema.PersonRoleList(**json.loads(person_inst.data))
            for person_inst in year_committee
        ],
    )
    search.add_document(
        type=schema.SearchDocumentType.YEAR,
        title=year_detail.title,
        id=year_id,
    )
    write_file(path, year_detail)
    return year_detail


def dump_year_index(year_details: List[schema.YearDetail]):
    path = make_out_path(Path("years"), "index")
    year_collection = schema.YearListCollection(
        [schema.YearList(**year_detail.dict()) for year_detail in year_details]
    )
    write_file(path, year_collection)


def dump_real_person(inst: database.Person) -> schema.PersonDetail:
    path = make_out_path(Path("people"), inst.id)
    person_detail = schema.PersonDetail(
        **{
            "content": inst.content,
            "show_roles": people.get_person_show_roles(inst.id),
            "committee_roles": people.get_person_committee_roles(inst.id),
            **json.loads(inst.data),
        }
    )
    search.add_document(
        type=schema.SearchDocumentType.PERSON,
        title=person_detail.title,
        id=inst.id,
    )
    write_file(path, person_detail)
    return person_detail


def dump_virtual_person(ref) -> schema.PersonDetail:
    path = make_out_path(Path("people"), ref.person_id)
    person_detail = schema.PersonDetail(
        id=ref.person_id,
        title=ref.person_name,
        show_roles=people.get_person_show_roles(ref.person_id),
        committee_roles=people.get_person_committee_roles(ref.person_id),
    )
    search.add_document(
        type=schema.SearchDocumentType.PERSON,
        title=person_detail.title,
        id=ref.person_id,
    )
    write_file(path, person_detail)
    return person_detail


def dump_people_by_committee_role(role_name: str):
    path = make_out_path(Path("roles/committee"), roles.get_role_id(role_name))
    collection = schema.PersonCommitteeRoleListCollection(
        roles.get_people_committee_roles_by_role(role_name)
    )
    write_file(path, collection)


def dump_crew_roles():
    write_file(
        path=make_out_path(Path("roles/crew"), "index"),
        obj=schema.RoleCollection(
            [
                schema.Role(role=role.name, aliases=list(role.aliases))
                for role in roles.CREW_ROLE_DEFINITIONS
            ]
        ),
    )


def dump_people_by_crew_role(role_name: str):
    path = make_out_path(Path("roles/crew"), roles.get_role_id(role_name))
    collection = schema.PersonShowRoleListCollection(
        roles.get_people_crew_roles_by_role(role_name)
    )
    write_file(path, collection)


def dump_people_if_cast():
    path = make_out_path(Path("roles"), "cast")
    collection = schema.PersonShowRoleListCollection(roles.get_people_cast())
    write_file(path, collection)


def dump_playwrights():
    path = make_out_path(Path("playwrights"), "index")
    collection = schema.PlaywrightCollection(
        playwrights.get_playwright_list(playwrights.get_playwright_shows())
    )
    write_file(path, collection)


def dump_plays():
    path = make_out_path(Path("plays"), "index")
    collection = schema.PlayCollection(
        playwrights.get_play_list(playwrights.get_play_shows())
    )
    write_file(path, collection)


def dump_search_documents():
    path = make_out_path(Path("search"), "documents")
    collection = schema.SearchDocumentCollection(search.get_search_documents())
    write_file(path, collection)


def dump_site_stats(site_stats: schema.SiteStats) -> None:
    path = make_out_path(Path(""), "index")
    write_file(path, site_stats)


@contextlib.contextmanager
def dump_action(title: str):
    log.info(title)
    tick = time.perf_counter()
    yield
    tock = time.perf_counter()
    log.debug(f"Took {tock - tick:.4f} seconds")


def dump_all():
    with dump_action("Writing OpenAPI spec"):
        spec.write_spec(OUTPUT_DIR / "openapi.json")

    with dump_action("Dumping shows"):
        shows = [dump_show(show_inst) for show_inst in database.Show.select()]

    with dump_action("Dumping years"):
        years_detail = [
            dump_year(year) for year in range(settings.year_start, settings.year_end)
        ]

    with dump_action("Dumping year index"):
        dump_year_index(years_detail)

    with dump_action("Dumping people with records"):
        real_people = [
            dump_real_person(person_inst) for person_inst in people.get_real_people()
        ]

    with dump_action("Dumping people without records"):
        real_people_ids = list(map(lambda x: x.id, real_people))
        virtual_people_query = people.get_people_from_roles(real_people_ids)
        virtual_people = [dump_virtual_person(ref) for ref in virtual_people_query]

    with dump_action("Dumping people by committee role"):
        [dump_people_by_committee_role(role) for role in roles.COMMITTEE_ROLES]

    with dump_action("Dumping people by crew role"):
        dump_crew_roles()
        [dump_people_by_crew_role(role) for role in roles.CREW_ROLES]

    with dump_action("Dumping people if cast"):
        dump_people_if_cast()

    with dump_action("Dumping playwrights"):
        dump_playwrights()

    with dump_action("Dumping plays"):
        dump_plays()

    with dump_action("Dumping search documents"):
        dump_search_documents()

    with dump_action("Dumping site stats"):
        dump_site_stats(
            schema.SiteStats(
                build_time=datetime.datetime.now(),
                branch=settings.branch,
                show_count=len(shows),
                person_count=len(real_people) + len(virtual_people),
            )
        )
