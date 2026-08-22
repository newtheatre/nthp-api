import datetime
import functools
import json
import logging
import shutil
import time
from pathlib import Path
from typing import NamedTuple, Protocol

import pydantic

from nthp_api.nthp_build import (
    assets,
    database,
    history,
    models,
    parallel,
    people,
    playwrights,
    roles,
    schema,
    search,
    seasons,
    shows,
    spec,
    trivia,
    venues,
    years,
)
from nthp_api.nthp_build.assets import AssetType
from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.parallel import (
    MP_CONTEXT,
    DumperSharedState,
    make_dumper_state,
)

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("dist")
STATIC_DIR = Path(__file__).parent / "static"


def delete_output_dir():
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def copy_static_files() -> None:
    """Copy the docs page, which renders the spec written alongside it."""
    shutil.copy(STATIC_DIR / "index.html", OUTPUT_DIR / "index.html")


def make_out_path(directory: Path, file: str) -> Path:
    path = OUTPUT_DIR / directory / Path(file + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_file(path: Path, obj: pydantic.BaseModel) -> None:
    with path.open("w") as f:
        f.write(
            obj.model_dump_json(by_alias=True, exclude_none=True, exclude_unset=True)
        )


def dump_specs(state: DumperSharedState):
    spec.write_spec(OUTPUT_DIR / "openapi.json")


def dump_show(inst: database.Show, state: DumperSharedState) -> schema.ShowDetail:
    path = make_out_path(Path("shows"), inst.id)
    show = shows.get_show_detail(inst)
    search.add_document(
        state=state,
        type=schema.SearchDocumentType.SHOW,
        title=show.title,
        id=inst.id,
        image_id=inst.primary_image,
        playwright=show.playwright,
        company=show.company,
        people=shows.get_show_people_names(show),
        plaintext=inst.plaintext,
    )
    write_file(path, show)
    return show


def dump_shows(state: DumperSharedState):
    for show_inst in database.Show.select():
        dump_show(show_inst, state)


def dump_year(year: int, state: DumperSharedState) -> schema.YearDetail:
    year_id = years.get_public_year_id(year)
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
        state=state,
        type=schema.SearchDocumentType.YEAR,
        title=year_detail.title,
        id=year_id,
    )
    write_file(path, year_detail)
    return year_detail


def dump_year_index(year_details: list[schema.YearDetail]):
    path = make_out_path(Path("years"), "index")
    year_collection = schema.YearListCollection(
        [schema.YearList(**year_detail.model_dump()) for year_detail in year_details]
    )
    write_file(path, year_collection)


def dump_years(state: DumperSharedState):
    years_detail = [
        dump_year(year, state) for year in range(settings.year_start, settings.year_end)
    ]

    dump_year_index(years_detail)


def dump_season(
    definition: seasons.SeasonDefinition, season_shows: list[database.Show]
) -> schema.SeasonList:
    path = make_out_path(Path("seasons"), seasons.get_season_id(definition))
    write_file(path, seasons.get_season_detail(definition, season_shows))
    return seasons.get_season_list(definition, season_shows)


def dump_season_index(season_lists: list[schema.SeasonList]):
    path = make_out_path(Path("seasons"), "index")
    write_file(path, schema.SeasonListCollection(season_lists))


def dump_seasons(state: DumperSharedState):
    season_lists = [
        dump_season(
            definition, seasons.get_season_shows(seasons.get_season_id(definition))
        )
        for definition in seasons.SEASON_DEFINITIONS
    ]
    dump_season_index(season_lists)


def dump_venue(
    inst: database.Venue, shows: list[database.Show], state: DumperSharedState
) -> schema.VenueDetail:
    path = make_out_path(Path("venues"), inst.id)
    venue_detail = venues.get_venue_detail(inst, shows)
    search.add_document(
        state=state,
        type=schema.SearchDocumentType.VENUE,
        title=venue_detail.name,
        id=inst.id,
    )
    write_file(path, venue_detail)
    return venue_detail


def dump_venue_index(query, show_venue_map: venues.ShowVenueMap):
    path = make_out_path(Path("venues"), "index")
    write_file(path, venues.get_venue_collection(query, show_venue_map))


def dump_venues(state: DumperSharedState):
    venue_query = database.Venue.select()
    show_venue_map = venues.get_show_venue_map(venue_query)
    [dump_venue(venue, show_venue_map[venue.id], state) for venue in venue_query]
    dump_venue_index(venue_query, show_venue_map)


def dump_real_person(
    inst: database.Person, state: DumperSharedState
) -> schema.PersonDetail:
    path = make_out_path(Path("people"), inst.id)
    source_data = models.Person(**json.loads(inst.data))
    person_detail = people.make_person_detail(source_data, inst.content)
    search.add_document(
        state=state,
        type=schema.SearchDocumentType.PERSON,
        title=person_detail.title,
        id=inst.id,
        image_id=inst.headshot,
    )
    write_file(path, person_detail)
    return person_detail


def dump_real_people(state: DumperSharedState):
    for person_inst in people.get_real_people():
        dump_real_person(person_inst, state)


def dump_virtual_person(ref, state: DumperSharedState) -> schema.PersonDetail:
    path = make_out_path(Path("people"), ref.person_id)
    person_detail = people.make_person_detail(people.make_virtual_person_model(ref))
    search.add_document(
        state=state,
        type=schema.SearchDocumentType.PERSON,
        title=person_detail.title,
        id=ref.person_id,
    )
    write_file(path, person_detail)
    return person_detail


def dump_virtual_people(state: DumperSharedState):
    real_people_ids = [x.id for x in database.Person.select(database.Person.id)]
    virtual_people_query = people.get_people_from_roles(excluded_ids=real_people_ids)
    for ref in virtual_people_query:
        dump_virtual_person(ref, state)


def make_person_index_item(
    model: models.Person,
    *,
    has_bio: bool,
    show_role_counts: dict[str, int],
    committee_role_counts: dict[str, int],
) -> schema.PersonIndexItem:
    assert model.id is not None, "Person model should have id by now"
    return schema.PersonIndexItem(
        id=model.id,
        title=model.title,
        submitted=model.submitted,
        headshot=model.headshot,
        graduated=people.get_graduation(model),
        show_role_count=show_role_counts.get(model.id, 0),
        committee_role_count=committee_role_counts.get(model.id, 0),
        has_bio=has_bio,
    )


def dump_people_index(state: DumperSharedState):
    """Index every person who gets a detail page, real and virtual alike."""
    path = make_out_path(Path("people"), "index")
    counts = {
        "show_role_counts": people.get_show_role_counts(),
        "committee_role_counts": people.get_committee_role_counts(),
    }

    real_people_ids = [inst.id for inst in database.Person.select(database.Person.id)]
    items = [
        make_person_index_item(
            models.Person(**json.loads(person_inst.data)), has_bio=True, **counts
        )
        for person_inst in people.get_real_people()
    ] + [
        make_person_index_item(
            people.make_virtual_person_model(ref), has_bio=False, **counts
        )
        for ref in people.get_people_from_roles(excluded_ids=real_people_ids)
    ]

    collection = schema.PersonIndexCollection(sorted(items, key=lambda item: item.id))
    write_file(path, collection)


def dump_collaborators_for_person(ref, state: DumperSharedState):
    path = make_out_path(Path("collaborators"), ref.person_id)
    collaborators = people.get_person_collaborators(ref.person_id)
    collection = schema.PersonCollaboratorCollection(list(collaborators))
    write_file(path, collection)


def dump_collaborators(state: DumperSharedState):
    people_query = people.get_people_from_roles()
    for ref in people_query:
        dump_collaborators_for_person(ref, state)


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
                schema.Role(role=role.name, aliases=sorted(role.aliases))
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


def dump_roles(state: DumperSharedState):
    [dump_people_by_committee_role(role) for role in roles.COMMITTEE_ROLES]
    dump_crew_roles()
    [dump_people_by_crew_role(role) for role in roles.CREW_ROLES]
    dump_people_if_cast()


def dump_show_trivia(show_id: str):
    path = make_out_path(Path("trivia/shows"), show_id)
    trivia_show = trivia.make_targeted_trivia(show_id, database.TargetType.SHOW)
    write_file(path, schema.TargetedTriviaCollection(trivia_show))


def dump_targeted_trivia(state: DumperSharedState):
    show_trivia_query = (
        database.Trivia.select(database.Trivia.target_id)
        .where(database.Trivia.target_type == database.TargetType.SHOW)
        .group_by(database.Trivia.target_id)
    )
    [dump_show_trivia(result.target_id) for result in show_trivia_query]


def dump_person_trivia(person_id: str):
    path = make_out_path(Path("trivia/people"), person_id)
    trivia_show = trivia.make_person_trivia(person_id)
    write_file(path, schema.PersonTriviaCollection(trivia_show))


def dump_people_trivia(state: DumperSharedState):
    people_trivia_query = (
        database.Trivia.select(database.Trivia.person_id)
        .where(database.Trivia.person_id.is_null(False))
        .group_by(database.Trivia.person_id)
    )
    for result in people_trivia_query:
        if result.person_id is not None:
            dump_person_trivia(result.person_id)


def dump_playwrights(state: DumperSharedState):
    path = make_out_path(Path("playwrights"), "index")
    collection = schema.PlaywrightCollection(
        playwrights.get_playwright_list(playwrights.get_playwright_shows())
    )
    write_file(path, collection)


def dump_plays(state: DumperSharedState):
    path = make_out_path(Path("plays"), "index")
    collection = schema.PlayCollection(
        playwrights.get_play_list(playwrights.get_play_shows())
    )
    write_file(path, collection)


def dump_history_records(state: DumperSharedState):
    path = make_out_path(Path("history"), "index")
    collection = schema.HistoryRecordCollection(history.get_history_records())
    write_file(path, collection)


def dump_album(album: database.Asset):
    path = make_out_path(Path("assets/album"), album.asset_id)
    asset_collection = assets.get_asset_collection_from_album(album)
    if asset_collection:
        write_file(path, asset_collection)


def dump_albums(state: DumperSharedState):
    albums_query = database.Asset.select().where(
        database.Asset.asset_type == AssetType.ALBUM
    )
    [dump_album(album) for album in albums_query]


def dump_site_stats(state: DumperSharedState) -> None:
    path = make_out_path(Path(), "index")
    write_file(
        path,
        schema.SiteStats(
            build_time=datetime.datetime.now(datetime.UTC),
            branch=settings.branch,
            show_count=database.Show.select().count(),
            person_count=people.get_people_from_roles().count(),
            person_with_bio_count=database.Person.select().count(),
            credit_count=database.PersonRole.select().count(),
            trivia_count=database.Trivia.select().count(),
        ),
    )


def dump_search_documents(state: DumperSharedState):
    path = make_out_path(Path("search"), "documents")
    collection = schema.SearchDocumentCollection(
        sorted(
            state.search_documents,
            key=lambda document: (document.type.value, document.id),
        )
    )
    write_file(path, collection)


class DumperFunc(Protocol):
    def __call__(self, state: DumperSharedState) -> None:
        pass


class Dumper(NamedTuple):
    name: str
    dumper: DumperFunc


DUMPERS: list[Dumper] = [
    Dumper("spec", dump_specs),
    Dumper("shows", dump_shows),
    Dumper("years", dump_years),
    Dumper("seasons", dump_seasons),
    Dumper("venues", dump_venues),
    Dumper("real people", dump_real_people),
    Dumper("virtual people", dump_virtual_people),
    Dumper("people index", dump_people_index),
    Dumper("collaborators", dump_collaborators),
    Dumper("roles", dump_roles),
    Dumper("targeted trivia", dump_targeted_trivia),
    Dumper("people trivia", dump_people_trivia),
    Dumper("playwrights", dump_playwrights),
    Dumper("plays", dump_plays),
    Dumper("history records", dump_history_records),
    Dumper("albums", dump_albums),
    Dumper("site stats", dump_site_stats),
]

POST_DUMPERS: list[Dumper] = [
    Dumper("search documents", dump_search_documents),
]


def run_dumper(dumper: Dumper, state: DumperSharedState):
    tick = time.perf_counter()
    dumper.dumper(state=state)
    tock = time.perf_counter()
    log.info(f"Dumped {dumper.name} in {tock - tick:.4f} seconds")


def dump_all():
    with MP_CONTEXT.Manager() as manager:
        state = make_dumper_state(manager)
        tasks = [functools.partial(run_dumper, dumper, state) for dumper in DUMPERS]
        parallel.run_cpu_tasks_in_parallel(tasks)
        [run_dumper(dumper, state) for dumper in POST_DUMPERS]
    copy_static_files()
    log.info("Dump complete")
