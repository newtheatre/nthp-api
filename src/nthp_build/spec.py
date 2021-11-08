import json
from pathlib import Path
from typing import List, Optional, Union

import pydantic.schema

from nthp_build import schema

JSON_SCHEMA = pydantic.schema.schema(
    (
        schema.PersonCommitteeRoleListCollection,
        schema.PersonDetail,
        schema.PersonShowRoleListCollection,
        schema.RoleCollection,
        schema.ShowDetail,
        schema.SiteStats,
        schema.YearDetail,
        schema.YearList,
        schema.YearListCollection,
    ),
    title="My Schema",
    ref_prefix="#/components/schemas/",
)


def check_model_present(model: str):
    if not model in JSON_SCHEMA["definitions"]:
        raise ValueError(f"Model {model} not found in JSON_SCHEMA")


def make_basic_get_operation(
    operation_id: str,
    tags: List[str],
    summary: str,
    model: str,
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
                            "schema": {"$ref": f"#/components/schemas/{model}"}
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
    model: str,
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
                            "schema": {"$ref": f"#/components/schemas/{model}"}
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
            model="SiteStats",
        ),
        "/years/index.json": make_basic_get_operation(
            operation_id="getYearList",
            tags=["years"],
            summary="Get year list",
            model="YearListCollection",
        ),
        "/years/{id}.json": make_detail_get_operation(
            operation_id="getYearDetail",
            tags=["years"],
            summary="Get year detail",
            model="YearDetail",
            key="id",
        ),
        "/shows/{id}.json": make_detail_get_operation(
            operation_id="getShowDetail",
            tags=["shows"],
            summary="Get show detail",
            model="ShowDetail",
            key="id",
        ),
        "/people/{id}.json": make_detail_get_operation(
            operation_id="getPersonDetail",
            tags=["people"],
            summary="Get person detail",
            model="PersonDetail",
            key="id",
        ),
        "/roles/committee/{name}.json": make_detail_get_operation(
            operation_id="getPeopleByCommitteeRole",
            tags=["roles"],
            summary="Get people by committee role",
            description="People are duplicated if they have held the position "
            "multiple times.",
            model="PersonCommitteeRoleListCollection",
            key="name",
        ),
        "/roles/crew/index.json": make_detail_get_operation(
            operation_id="getCrewRoles",
            tags=["roles"],
            summary="Get list of crew roles",
            model="RoleCollection",
            key="name",
        ),
        "/roles/crew/{name}.json": make_detail_get_operation(
            operation_id="getPeopleByCrewRole",
            tags=["roles"],
            summary="Get people by committee role",
            description="People are not duplicated.",
            model="PersonShowRoleListCollection",
            key="name",
        ),
        "/roles/cast.json": make_detail_get_operation(
            operation_id="getPeopleCast",
            tags=["roles"],
            summary="Get people if cast in any show",
            description="People are not duplicated. ",
            model="PersonShowRoleListCollection",
            key="name",
        ),
    },
    "components": {"schemas": JSON_SCHEMA["definitions"]},
}


def write_spec(path: Union[str, Path]):
    with open(path, "w") as f:
        json.dump(SPEC, f, indent=4)


if __name__ == "__main__":
    write_spec("openapi.json")
