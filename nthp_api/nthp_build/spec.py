import json
from pathlib import Path

import pydantic.schema
from pydantic_collections import BaseCollectionModel

from nthp_api.nthp_build import schema

JSON_SCHEMA = pydantic.schema.schema(
    (
        schema.AssetCollection,
        schema.HistoryRecordCollection,
        schema.PersonCollaboratorCollection,
        schema.PersonCommitteeRoleListCollection,
        schema.PersonDetail,
        schema.PersonShowRoleListCollection,
        schema.PersonTriviaCollection,
        schema.PlayCollection,
        schema.PlaywrightCollection,
        schema.RoleCollection,
        schema.SearchDocumentCollection,
        schema.ShowDetail,
        schema.SiteStats,
        schema.TargetedTriviaCollection,
        schema.VenueCollection,
        schema.VenueDetail,
        schema.YearDetail,
        schema.YearList,
        schema.YearListCollection,
    ),
    title="My Schema",
    ref_prefix="#/components/schemas/",
)

Model = type[schema.NthpSchema] | type[BaseCollectionModel]


def check_model_present(model: Model):
    if model.__name__ not in JSON_SCHEMA["definitions"]:
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


def make_detail_get_operation(  # noqa: PLR0913
    operation_id: str,
    tags: list[str],
    summary: str,
    model: Model,
    key: str,
    description: str | None = None,
):
    check_model_present(model)
    return {
        "get": {
            "operationId": operation_id,
            "tags": tags,
            "summary": summary,
            "description": description,
            "parameters": [
                {
                    "name": key,
                    "in": "path",
                    "required": True,
                    "schema": {
                        "type": "string",
                    },
                },
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


SPEC = {
    "openapi": "3.1.0",
    "info": {
        "title": "New Theatre History Project API",
        "version": "0.0.1",
        "description": "API for serving the content for the New Theatre History "
        "Project. The API is generated from the content repo.",
    },
    "servers": [
        {
            "url": "https://nthp-api.wjdp.uk/v1/{branch}",
            "description": "Production server",
            "variables": {
                "branch": {
                    "default": "master",
                    "description": "The branch of the content repo, currently only "
                    "supports master.",
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
            model=schema.YearDetail,
            key="id",
        ),
        "/shows/{id}.json": make_detail_get_operation(
            operation_id="getShowDetail",
            tags=["shows"],
            summary="Get show detail",
            model=schema.ShowDetail,
            key="id",
        ),
        "/venues/index.json": make_basic_get_operation(
            operation_id="getVenueList",
            tags=["venues"],
            summary="Get list of venues",
            description="Listing of known venues.",
            model=schema.VenueCollection,
        ),
        "/venues/{id}.json": make_detail_get_operation(
            operation_id="getVenueDetail",
            tags=["venues"],
            summary="Get venue detail",
            description="Details of a single venue, including show list.",
            model=schema.VenueDetail,
            key="id",
        ),
        "/people/{id}.json": make_detail_get_operation(
            operation_id="getPersonDetail",
            tags=["people"],
            summary="Get person detail",
            model=schema.PersonDetail,  # type: ignore
            key="id",
        ),
        "/collaborators/{id}.json": make_detail_get_operation(
            operation_id="getPersonCollaborators",
            tags=["people"],
            summary="Get person collaborators",
            model=schema.PersonCollaboratorCollection,
            key="id",
        ),
        "/roles/committee/{name}.json": make_detail_get_operation(
            operation_id="getPeopleByCommitteeRole",
            tags=["roles"],
            summary="Get people by committee role",
            description="People are duplicated if they have held the position "
            "multiple times.",
            model=schema.PersonCommitteeRoleListCollection,
            key="name",
        ),
        "/roles/crew/index.json": make_basic_get_operation(
            operation_id="getCrewRoles",
            tags=["roles"],
            summary="Get list of crew roles",
            model=schema.RoleCollection,
        ),
        "/roles/crew/{name}.json": make_detail_get_operation(
            operation_id="getPeopleByCrewRole",
            tags=["roles"],
            summary="Get people by committee role",
            description="People are not duplicated.",
            model=schema.PersonShowRoleListCollection,
            key="name",
        ),
        "/roles/cast.json": make_basic_get_operation(
            operation_id="getPeopleCast",
            tags=["roles"],
            summary="Get people if cast in any show",
            description="People are not duplicated. ",
            model=schema.PersonShowRoleListCollection,
        ),
        "/trivia/shows/{id}.json": make_detail_get_operation(
            operation_id="getShowTrivia",
            tags=["trivia"],
            summary="Get show trivia",
            description="A collection of trivia for a show. If response is 404 then "
            "the show doesn't have trivia yet.",
            model=schema.TargetedTriviaCollection,
            key="id",
        ),
        "/trivia/people/{id}.json": make_detail_get_operation(
            operation_id="getPersonTrivia",
            tags=["trivia"],
            summary="Get person trivia",
            description="A collection of trivia for a person. If response is 404 then "
            "the person hasn't submitted any trivia yet.",
            model=schema.PersonTriviaCollection,
            key="id",
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
            model=schema.SearchDocumentCollection,
        ),
    },
    "components": {"schemas": JSON_SCHEMA["definitions"]},
}


def write_spec(path: str | Path):
    if isinstance(path, str):
        path = Path(path)
    with path.open("w") as f:
        json.dump(SPEC, f, indent=4)


if __name__ == "__main__":
    write_spec("openapi.json")
