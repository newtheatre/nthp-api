import json
from pathlib import Path
from typing import List, Optional, Type, Union

import pydantic.schema
from pydantic_collections import BaseCollectionModel

from nthp_build import schema

JSON_SCHEMA = pydantic.schema.schema(
    (
        schema.PersonCommitteeRoleListCollection,
        schema.PersonDetail,
        schema.PersonShowRoleListCollection,
        schema.PlaywrightCollection,
        schema.RoleCollection,
        schema.SearchDocumentCollection,
        schema.ShowDetail,
        schema.SiteStats,
        schema.YearDetail,
        schema.YearList,
        schema.YearListCollection,
    ),
    title="My Schema",
    ref_prefix="#/components/schemas/",
)

Model = Union[Type[schema.NthpSchema], Type[BaseCollectionModel]]


def check_model_present(model: Model):
    if not model.__name__ in JSON_SCHEMA["definitions"]:
        raise ValueError(f"Model {model} not found in JSON_SCHEMA")


def make_basic_get_operation(
    operation_id: str,
    tags: List[str],
    summary: str,
    model: Model,
    description: Optional[str] = None,
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


def make_detail_get_operation(
    operation_id: str,
    tags: List[str],
    summary: str,
    model: Model,
    key: str,
    description: Optional[str] = None,
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
        "/people/{id}.json": make_detail_get_operation(
            operation_id="getPersonDetail",
            tags=["people"],
            summary="Get person detail",
            model=schema.PersonDetail,  # type: ignore
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
        "/playwrights/index.json": make_basic_get_operation(
            operation_id="getPlaywrights",
            tags=["playwrights"],
            summary="Get list of playwrights and shows performed",
            model=schema.PlaywrightCollection,
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


def write_spec(path: Union[str, Path]):
    with open(path, "w") as f:
        json.dump(SPEC, f, indent=4)


if __name__ == "__main__":
    write_spec("openapi.json")
