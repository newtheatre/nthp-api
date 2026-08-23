import datetime
import functools
import json
import logging
import shutil
import time
from pathlib import Path
from typing import NamedTuple, Protocol

import pydantic
from pydantic_collections import BaseCollectionModel

from nthp_api.nthp_build import (
    assets,
    content_schema,
    content_schema_docs,
    database,
    history,
    homepage,
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
from nthp_api.nthp_build.version import get_version

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("dist")
CONTENT_SCHEMA_DIR = Path("content-schema")
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
    """
    Write a document, with one serialisation for every path.

    Null scalars are omitted rather than sent as null; lists are always emitted, as
    no schema field is both a list and nullable, so an empty list stays an empty
    list rather than vanishing. Nothing turns on whether a field was set explicitly.
    """
    with path.open("w") as f:
        f.write(obj.model_dump_json(by_alias=True, exclude_none=True))


def dump_specs(state: DumperSharedState):
    spec.write_spec(OUTPUT_DIR / "openapi.json")


def dump_content_schema(state: DumperSharedState) -> None:
    """
    Publish the shape of the content repo alongside the shape of the API.

    Editors validate their front matter against these, and the page beside them
    is what a person reads instead.
    """
    directory = OUTPUT_DIR / CONTENT_SCHEMA_DIR
    content_schema.write_document_schemas(directory)
    (directory / "index.html").write_text(content_schema_docs.render_html())


def dump_show(
    inst: database.Show,
    state: DumperSharedState,
    previous: schema.ShowRef | None = None,
    next_show: schema.ShowRef | None = None,
) -> schema.ShowDetail:
    path = make_out_path(Path("shows"), inst.id)
    show = shows.get_show_detail(inst, previous=previous, next_show=next_show)
    search.add_document(state, search.get_show_document(inst, show))
    write_file(path, show)
    return show


def dump_show_index(show_insts: list[database.Show]):
    path = make_out_path(Path("shows"), "index")
    write_file(
        path,
        schema.ShowIndexCollection(
            [shows.get_show_index_item(show_inst) for show_inst in show_insts]
        ),
    )


def dump_shows(state: DumperSharedState):
    """Dump every show, in canonical order so each knows its neighbours."""
    show_insts = list(shows.get_show_query())
    sequence_items = [shows.get_show_ref(inst) for inst in show_insts]
    last_index = len(show_insts) - 1
    for index, show_inst in enumerate(show_insts):
        dump_show(
            show_inst,
            state,
            previous=sequence_items[index - 1] if index > 0 else None,
            next_show=sequence_items[index + 1] if index < last_index else None,
        )
    dump_show_index(show_insts)


def dump_year(
    year: int,
    state: DumperSharedState,
    award_holders: dict[str, dict[str, list[schema.PersonRef]]],
) -> schema.YearDetail:
    year_id = years.get_public_year_id(year)
    path = make_out_path(Path("years"), year_id)
    year_shows = shows.get_show_query().where(database.Show.year_id == year_id)
    year_committee = database.PersonRole.select().where(
        database.PersonRole.target_type == database.PersonRoleType.COMMITTEE,
        database.PersonRole.target_id == year_id,
    )
    year_detail = schema.YearDetail(
        **dict(schema.YearRef.from_start_year(year)),
        show_count=len(year_shows),
        shows=[shows.get_show_list_item(show_inst) for show_inst in year_shows],
        committee=people.make_person_credits(
            models.PersonRole(**json.loads(person_inst.data))
            for person_inst in year_committee
        ),
        fellows=award_holders.get(year_id, {}).get(models.Award.FELLOWSHIP, []),
        commendations=award_holders.get(year_id, {}).get(models.Award.COMMENDATION, []),
    )
    search.add_document(state, search.get_year_document(year_detail))
    write_file(path, year_detail)
    return year_detail


def dump_year_index(year_details: list[schema.YearDetail]):
    path = make_out_path(Path("years"), "index")
    year_collection = schema.YearListCollection(
        [schema.YearList(**year_detail.model_dump()) for year_detail in year_details]
    )
    write_file(path, year_collection)


def dump_years(state: DumperSharedState):
    award_holders = people.get_award_holders()
    years_detail = [
        dump_year(year, state, award_holders)
        for year in range(settings.year_start, settings.year_end)
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
    record: venues.VenueRecord, state: DumperSharedState
) -> schema.VenueList:
    path = make_out_path(Path("venues"), record.id)
    write_file(path, venues.get_venue_detail(record))
    search.add_document(state, search.get_venue_document(record))
    return venues.get_venue_list(record)


def dump_venue_index(venue_lists: list[schema.VenueList]):
    path = make_out_path(Path("venues"), "index")
    write_file(path, schema.VenueCollection(venue_lists))


def dump_venues(state: DumperSharedState):
    venue_lists = [dump_venue(record, state) for record in venues.get_venue_records()]
    dump_venue_index(venue_lists)


def dump_real_person(
    inst: database.Person,
    state: DumperSharedState,
    crew_role_canonical_names: dict[str, str],
) -> schema.PersonDetail:
    path = make_out_path(Path("people"), inst.id)
    source_data = models.Person(**json.loads(inst.data))
    person_detail = people.make_person_detail(
        source_data,
        inst.content,
        trivia=trivia.make_person_trivia(inst.id),
        has_bio=True,
    )
    search.add_document(
        state,
        search.get_person_document(
            person_detail,
            crew_role_canonical_names,
            has_bio=True,
            plaintext=inst.plaintext,
        ),
    )
    write_file(path, person_detail)
    return person_detail


def dump_real_people(state: DumperSharedState):
    crew_role_canonical_names = roles.get_crew_role_canonical_names()
    for person_inst in people.get_real_people():
        dump_real_person(person_inst, state, crew_role_canonical_names)


def dump_virtual_person(
    ref, state: DumperSharedState, crew_role_canonical_names: dict[str, str]
) -> schema.PersonDetail:
    path = make_out_path(Path("people"), ref.person_id)
    person_detail = people.make_person_detail(
        people.make_virtual_person_model(ref),
        trivia=trivia.make_person_trivia(ref.person_id),
        has_bio=False,
    )
    search.add_document(
        state,
        search.get_person_document(
            person_detail, crew_role_canonical_names, has_bio=False
        ),
    )
    write_file(path, person_detail)
    return person_detail


def dump_virtual_people(state: DumperSharedState):
    crew_role_canonical_names = roles.get_crew_role_canonical_names()
    real_people_ids = [x.id for x in database.Person.select(database.Person.id)]
    virtual_people_query = people.get_people_from_roles(excluded_ids=real_people_ids)
    for ref in virtual_people_query:
        dump_virtual_person(ref, state, crew_role_canonical_names)


def make_person_index_item(
    model: models.Person,
    *,
    has_bio: bool,
    show_role_counts: dict[str, int],
    committee_role_counts: dict[str, int],
) -> schema.PersonIndexItem:
    assert model.id is not None, "Person model should have id by now"
    submitted, submitted_date = people.get_submission(model.submitted)
    return schema.PersonIndexItem(
        id=model.id,
        title=model.title,
        submitted=submitted,
        submitted_date=submitted_date,
        headshot=assets.get_image_ref(model.headshot),
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


def dump_collaborators(state: DumperSharedState):
    index = people.CollaboratorIndex()
    for ref in people.get_people_from_roles():
        path = make_out_path(Path("collaborators"), ref.person_id)
        write_file(
            path, schema.PersonCollaboratorCollection(index.for_person(ref.person_id))
        )


def dump_people_by_committee_role(definition: roles.RoleDefinition):
    path = make_out_path(Path("roles/committee"), roles.get_role_id(definition.name))
    collection = schema.PersonCommitteeRoleListCollection(
        roles.get_people_committee_roles_by_role(definition)
    )
    write_file(path, collection)


def dump_committee_roles(definitions: list[roles.RoleDefinition]):
    write_file(
        path=make_out_path(Path("roles/committee"), "index"),
        obj=schema.RoleCollection(
            [
                roles.get_role_list(definition, database.PersonRoleType.COMMITTEE)
                for definition in definitions
            ]
        ),
    )


def dump_crew_roles(definitions: list[roles.RoleDefinition]):
    write_file(
        path=make_out_path(Path("roles/crew"), "index"),
        obj=schema.RoleCollection(
            [
                roles.get_role_list(definition, database.PersonRoleType.CREW)
                for definition in definitions
            ]
        ),
    )


def dump_people_by_crew_role(definition: roles.RoleDefinition):
    path = make_out_path(Path("roles/crew"), roles.get_role_id(definition.name))
    collection = schema.PersonShowRoleListCollection(
        roles.get_people_crew_roles_by_role(definition)
    )
    write_file(path, collection)


def dump_people_if_cast():
    path = make_out_path(Path("roles"), "cast")
    collection = schema.PersonShowRoleListCollection(roles.get_people_cast())
    write_file(path, collection)


def dump_roles(state: DumperSharedState):
    committee_definitions = roles.get_committee_role_definitions()
    dump_committee_roles(committee_definitions)
    for definition in committee_definitions:
        dump_people_by_committee_role(definition)

    crew_definitions = roles.get_crew_role_definitions()
    dump_crew_roles(crew_definitions)
    for definition in crew_definitions:
        dump_people_by_crew_role(definition)

    dump_people_if_cast()


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


def dump_on_this_day(state: DumperSharedState) -> None:
    """Write a file per day of the year, the leap day included, empty ones and all."""
    shows_by_day = homepage.get_shows_by_day_of_year()
    for day_of_year in homepage.get_days_of_year():
        write_file(
            make_out_path(
                Path("on-this-day"), homepage.get_day_of_year_id(day_of_year)
            ),
            schema.OnThisDayShowCollection(shows_by_day.get(day_of_year, [])),
        )


def dump_posters(state: DumperSharedState) -> None:
    path = make_out_path(Path("assets"), "posters")
    write_file(path, schema.PosterCollection(homepage.get_poster_items()))


def dump_site_stats(state: DumperSharedState) -> None:
    path = make_out_path(Path(), "index")
    write_file(
        path,
        schema.SiteStats(
            build_time=datetime.datetime.now(datetime.UTC),
            branch=settings.branch,
            api_version=get_version(),
            build_number=settings.build_number,
            commit=settings.commit,
            show_count=database.Show.select().count(),
            person_count=people.get_people_from_roles().count(),
            person_with_bio_count=database.Person.select().count(),
            person_with_headshot_count=database.Person.select()
            .where(database.Person.headshot.is_null(False))
            .count(),
            show_with_image_count=database.Show.select()
            .where(database.Show.primary_image.is_null(False))
            .count(),
            venue_count=len(venues.get_venue_records()),
            credit_count=database.PersonRole.select().count(),
            trivia_count=database.Trivia.select().count(),
            search_document_count=len(state.search_documents),
            year_count=settings.year_end - settings.year_start,
            first_year_id=years.get_public_year_id(settings.year_start),
            latest_year_id=years.get_public_year_id(settings.year_end - 1),
        ),
    )


SEARCH_DOCUMENT_COLLECTIONS: dict[
    schema.SearchDocumentType, type[BaseCollectionModel]
] = {
    schema.SearchDocumentType.SHOW: schema.SearchDocumentShowCollection,
    schema.SearchDocumentType.PERSON: schema.SearchDocumentPersonCollection,
    schema.SearchDocumentType.VENUE: schema.SearchDocumentVenueCollection,
    schema.SearchDocumentType.YEAR: schema.SearchDocumentYearCollection,
}


def dump_search_documents(state: DumperSharedState):
    """Write the whole corpus, and a file per type for consumers indexing one."""
    documents = sorted(
        state.search_documents,
        key=lambda document: (document.type.value, document.id),
    )
    write_file(
        make_out_path(Path("search"), "documents"),
        schema.SearchDocumentCollection(documents),
    )
    for document_type, collection_model in SEARCH_DOCUMENT_COLLECTIONS.items():
        write_file(
            make_out_path(Path("search/documents"), document_type.value),
            collection_model(
                [document for document in documents if document.type == document_type]
            ),
        )


class DumperFunc(Protocol):
    def __call__(self, state: DumperSharedState) -> None:
        pass


class Dumper(NamedTuple):
    name: str
    dumper: DumperFunc


DUMPERS: list[Dumper] = [
    Dumper("spec", dump_specs),
    Dumper("content schema", dump_content_schema),
    Dumper("shows", dump_shows),
    Dumper("years", dump_years),
    Dumper("seasons", dump_seasons),
    Dumper("venues", dump_venues),
    Dumper("real people", dump_real_people),
    Dumper("virtual people", dump_virtual_people),
    Dumper("people index", dump_people_index),
    Dumper("collaborators", dump_collaborators),
    Dumper("roles", dump_roles),
    Dumper("playwrights", dump_playwrights),
    Dumper("plays", dump_plays),
    Dumper("history records", dump_history_records),
    Dumper("albums", dump_albums),
    Dumper("on this day", dump_on_this_day),
    Dumper("posters", dump_posters),
]

# Run once the parallel dumpers have filled the shared state: the search corpus is
# built from what they emit, and the site stats count it.
POST_DUMPERS: list[Dumper] = [
    Dumper("search documents", dump_search_documents),
    Dumper("site stats", dump_site_stats),
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
