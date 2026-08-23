import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel
from pydantic.json_schema import JsonSchemaMode, models_json_schema
from pydantic_collections import BaseCollectionModel

from nthp_api.nthp_build import content_schema, schema
from nthp_api.nthp_build.version import get_version


def make_models_json_schema_models(
    *models: type[BaseModel],
) -> Sequence[tuple[type[BaseModel], JsonSchemaMode]]:
    json_schema_mode: JsonSchemaMode = "validation"
    return [(model, json_schema_mode) for model in models]


PYDANTIC_JSON_SCHEMA = models_json_schema(
    make_models_json_schema_models(
        schema.AssetCollection,
        schema.HistoryRecordCollection,
        schema.OnThisDayShowCollection,
        schema.PersonCollaboratorCollection,
        schema.PersonCommitteeRoleListCollection,
        schema.PersonDetail,
        schema.PersonIndexCollection,
        schema.PersonShowRoleListCollection,
        schema.PlayCollection,
        schema.PlaywrightCollection,
        schema.PosterCollection,
        schema.RoleCollection,
        schema.SearchDocumentCollection,
        schema.SearchDocumentPersonCollection,
        schema.SearchDocumentShowCollection,
        schema.SearchDocumentVenueCollection,
        schema.SearchDocumentYearCollection,
        schema.SeasonDetail,
        schema.SeasonListCollection,
        schema.ShowDetail,
        schema.ShowIndexCollection,
        schema.SiteStats,
        schema.VenueCollection,
        schema.VenueDetail,
        schema.YearDetail,
        schema.YearList,
        schema.YearListCollection,
    ),
    title="My Schema",
    ref_template="#/components/schemas/{model}",
)

JSON_SCHEMA = PYDANTIC_JSON_SCHEMA[1]["$defs"]

Model = type[schema.NthpSchema] | type[BaseCollectionModel]


def check_model_present(model: Model):
    if model.__name__ not in JSON_SCHEMA:
        raise ValueError(f"Model {model} not found in JSON_SCHEMA")


def make_basic_get_operation(
    operation_id: str,
    tags: list[str],
    summary: str,
    model: Model,
    description: str | None = None,
):
    check_model_present(model)
    return {
        "get": {
            "operationId": operation_id,
            "tags": tags,
            "summary": summary,
            "description": description,
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{model.__name__}"}
                        }
                    },
                }
            },
        }
    }


def make_detail_get_operation(  # noqa: PLR0913, PLR0917
    operation_id: str,
    tags: list[str],
    summary: str,
    model: Model,
    key: str | list[str],
    description: str | None = None,
):
    check_model_present(model)
    keys = [key] if isinstance(key, str) else key
    return {
        "get": {
            "operationId": operation_id,
            "tags": tags,
            "summary": summary,
            "description": description,
            "parameters": [
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "schema": {
                        "type": "string",
                    },
                }
                for name in keys
            ],
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{model.__name__}"}
                        }
                    },
                },
                "404": {
                    "description": "Not Found",
                },
            },
        }
    }


def make_content_schema_get_operation() -> dict:
    """`/content-schema/{type}.json` — one JSON Schema document per content type.

    These describe the content repo's front matter, not the API's responses,
    so the response is a generic JSON Schema object rather than a pydantic
    model.
    """
    type_names = [
        document_type.name for document_type in content_schema.CONTENT_DOCUMENT_TYPES
    ]
    return {
        "get": {
            "operationId": "getContentSchema",
            "tags": ["content-schema"],
            "summary": "Get a content document's JSON Schema",
            "description": "The JSON Schema (draft 2020-12) an editor validates a "
            "content repo front matter document against before submitting it. "
            "For people, not machines: content editors and agents authoring or "
            "checking `show`, `person`, `venue`, `committee`, `history`, `roles` "
            "and `link-types` documents in the content repo. See "
            "`content-schema/index.html` for a human-readable rendering of the "
            "same schemas.",
            "parameters": [
                {
                    "name": "type",
                    "in": "path",
                    "required": True,
                    "schema": {
                        "type": "string",
                        "enum": type_names,
                    },
                }
            ],
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                },
                "404": {
                    "description": "Not Found",
                },
            },
        }
    }


SPEC = {
    "openapi": "3.1.0",
    "info": {
        "title": "New Theatre History Project API",
        "version": get_version(),
        "description": "API for serving the content for the New Theatre History "
        "Project. The API is generated from the content repo.",
    },
    "servers": [
        {
            "url": "https://nthp-api.newtheatre.org.uk/v1/{branch}",
            "description": "Production",
            "variables": {
                "branch": {
                    "default": "master",
                    "description": "The production branch of the content repo.",
                }
            },
        }
    ],
    "paths": {
        "/index.json": make_basic_get_operation(
            operation_id="getSiteStats",
            tags=["site"],
            summary="Get site stats",
            description="Top level statistics for the site, includes counts of records "
            "and build information.",
            model=schema.SiteStats,
        ),
        "/years/index.json": make_basic_get_operation(
            operation_id="getYearList",
            tags=["years"],
            summary="Get year list",
            model=schema.YearListCollection,
        ),
        "/years/{id}.json": make_detail_get_operation(
            operation_id="getYearDetail",
            tags=["years"],
            summary="Get year detail",
            description="Academic years are identified as `YYYY-YY`, e.g. `2024-25`, "
            "and `decade` is the calendar year the decade begins in, e.g. `2020`. "
            "Fellows and commendations are the people awarded them who graduated in "
            "the year. The committee is a list of credits, the same shape as a "
            "show's cast and crew.",
            model=schema.YearDetail,
            key="id",
        ),
        "/shows/index.json": make_basic_get_operation(
            operation_id="getShowIndex",
            tags=["shows"],
            summary="Get index of shows",
            description="Every show in the archive's canonical order: academic year, "
            "then season order within the year, then date. Lighter than the show "
            "lists embedded in year and season documents.",
            model=schema.ShowIndexCollection,
        ),
        "/shows/{yearId}/{slug}.json": make_detail_get_operation(
            operation_id="getShowDetail",
            tags=["shows"],
            summary="Get show detail",
            description="Shows are identified as `{yearId}/{slug}`, "
            "e.g. `2024-25/macbeth`.",
            model=schema.ShowDetail,
            key=["yearId", "slug"],
        ),
        "/seasons/index.json": make_basic_get_operation(
            operation_id="getSeasonList",
            tags=["seasons"],
            summary="Get list of seasons",
            description="Every known season, including those with no shows.",
            model=schema.SeasonListCollection,
        ),
        "/seasons/{id}.json": make_detail_get_operation(
            operation_id="getSeasonDetail",
            tags=["seasons"],
            summary="Get season detail",
            description="Details of a single season, including show list. Seasons "
            "renamed over the years are merged into the current name, the old names "
            "listed as aliases.",
            model=schema.SeasonDetail,
            key="id",
        ),
        "/venues/index.json": make_basic_get_operation(
            operation_id="getVenueList",
            tags=["venues"],
            summary="Get list of venues",
            description="Every venue referenced by a show, whether documented in the "
            "archive or not, sorted by id.",
            model=schema.VenueCollection,
        ),
        "/venues/{id}.json": make_detail_get_operation(
            operation_id="getVenueDetail",
            tags=["venues"],
            summary="Get venue detail",
            description="Details of a single venue, including show list. Venues with "
            "no document of their own are stubs, carrying only name, shows and "
            "grouping; sentinel venues stand in for an unknown or online venue.",
            model=schema.VenueDetail,
            key="id",
        ),
        "/people/index.json": make_basic_get_operation(
            operation_id="getPersonIndex",
            tags=["people"],
            summary="Get index of people",
            description="Every person with a detail page, real and virtual, sorted "
            "by id.",
            model=schema.PersonIndexCollection,
        ),
        "/people/{id}.json": make_detail_get_operation(
            operation_id="getPersonDetail",
            tags=["people"],
            summary="Get person detail",
            description="Everything known about a person, including their links and "
            "news. `student` is worked out from the graduation year and the date the "
            "API was built, so it goes stale between builds, as is the `estimated` "
            "graduation year. `submitted` says whether the person submitted the "
            "record; `submittedDate` gives the date where one was authored.",
            model=schema.PersonDetail,  # type: ignore
            key="id",
        ),
        "/collaborators/{id}.json": make_detail_get_operation(
            operation_id="getPersonCollaborators",
            tags=["people"],
            summary="Get person collaborators",
            description="Everyone the person shares a show or a committee with, and "
            "the ids of what they shared.",
            model=schema.PersonCollaboratorCollection,
            key="id",
        ),
        "/roles/committee/index.json": make_basic_get_operation(
            operation_id="getCommitteeRoles",
            tags=["roles"],
            summary="Get list of committee roles",
            description="Every committee role held, near-duplicate titles merged into "
            "one role with the others listed as aliases. Link to a role by its `id`, "
            "never by a slug derived from its name.",
            model=schema.RoleCollection,
        ),
        "/roles/committee/{id}.json": make_detail_get_operation(
            operation_id="getPeopleByCommitteeRole",
            tags=["roles"],
            summary="Get people by committee role",
            description="People are duplicated if they have held the position "
            "multiple times.",
            model=schema.PersonCommitteeRoleListCollection,
            key="id",
        ),
        "/roles/crew/index.json": make_basic_get_operation(
            operation_id="getCrewRoles",
            tags=["roles"],
            summary="Get list of crew roles",
            description="Crew roles as defined by the content repo's "
            "`_data/roles.yaml`, in the order defined there. Link to a role by its "
            "`id`, never by a slug derived from its name.",
            model=schema.RoleCollection,
        ),
        "/roles/crew/{id}.json": make_detail_get_operation(
            operation_id="getPeopleByCrewRole",
            tags=["roles"],
            summary="Get people by crew role",
            description="People are not duplicated.",
            model=schema.PersonShowRoleListCollection,
            key="id",
        ),
        "/roles/cast.json": make_basic_get_operation(
            operation_id="getPeopleCast",
            tags=["roles"],
            summary="Get people if cast in any show",
            description="People are not duplicated. ",
            model=schema.PersonShowRoleListCollection,
        ),
        "/on-this-day/{date}.json": make_detail_get_operation(
            operation_id="getOnThisDay",
            tags=["shows"],
            summary="Get shows running on a day of the year",
            description="Days are identified as `MM-DD`, e.g. `11-13`; every day of "
            "the year has a file, the leap day included, and days nothing was running "
            "on hold an empty list. A show matches where the day falls within its run, "
            "both ends included; shows dated only to the month or year are left out. "
            "Shows are ordered by year.",
            model=schema.OnThisDayShowCollection,
            key="date",
        ),
        "/assets/posters.json": make_basic_get_operation(
            operation_id="getPosters",
            tags=["assets"],
            summary="Get the poster pool",
            description="Every show with a primary image, in the archive's canonical "
            "show order; each item is a show reference whose `primaryImage` is always "
            "present. Consumers pick from the pool themselves; the API does not "
            "shuffle it.",
            model=schema.PosterCollection,
        ),
        "/assets/album/{id}.json": make_detail_get_operation(
            operation_id="getAlbumAssets",
            tags=["assets"],
            summary="Get album assets",
            description="A collection of assets for an album. If response is 404 then "
            "the album either doesn't exist or has no assets.",
            model=schema.AssetCollection,
            key="id",
        ),
        "/playwrights/index.json": make_basic_get_operation(
            operation_id="getPlaywrights",
            tags=["playwrights"],
            summary="Get list of playwrights and shows performed",
            model=schema.PlaywrightCollection,
        ),
        "/plays/index.json": make_basic_get_operation(
            operation_id="getPlays",
            tags=["plays"],
            summary="Get list of plays and shows performed",
            model=schema.PlayCollection,
        ),
        "/history/index.json": make_basic_get_operation(
            operation_id="getHistoryRecords",
            tags=["history"],
            summary="Get list of history records",
            model=schema.HistoryRecordCollection,
        ),
        "/search/documents.json": make_basic_get_operation(
            operation_id="getSearchDocuments",
            tags=["search"],
            summary="Get search documents",
            description="The whole search corpus, sorted by type then id. Documents "
            "are a union discriminated on `type`, each carrying the fields worth "
            "searching or filtering on for what it describes. The API ships fields, "
            "not an index; the consumer builds its own. Search documents are the one "
            "place references are flattened to `{entity}Id` fields, and the record's "
            "image to `imageId`, to keep the corpus small.",
            model=schema.SearchDocumentCollection,
        ),
        "/search/documents/show.json": make_basic_get_operation(
            operation_id="getShowSearchDocuments",
            tags=["search"],
            summary="Get show search documents",
            description="The show slice of the search corpus.",
            model=schema.SearchDocumentShowCollection,
        ),
        "/search/documents/person.json": make_basic_get_operation(
            operation_id="getPersonSearchDocuments",
            tags=["search"],
            summary="Get person search documents",
            description="The person slice of the search corpus.",
            model=schema.SearchDocumentPersonCollection,
        ),
        "/search/documents/venue.json": make_basic_get_operation(
            operation_id="getVenueSearchDocuments",
            tags=["search"],
            summary="Get venue search documents",
            description="The venue slice of the search corpus.",
            model=schema.SearchDocumentVenueCollection,
        ),
        "/search/documents/year.json": make_basic_get_operation(
            operation_id="getYearSearchDocuments",
            tags=["search"],
            summary="Get year search documents",
            description="The year slice of the search corpus.",
            model=schema.SearchDocumentYearCollection,
        ),
        "/content-schema/{type}.json": make_content_schema_get_operation(),
    },
    "components": {"schemas": JSON_SCHEMA},
}


def write_spec(path: str | Path):
    if isinstance(path, str):
        path = Path(path)
    with path.open("w") as f:
        json.dump(SPEC, f, indent=4)


if __name__ == "__main__":
    write_spec("openapi.json")
