import json
from pathlib import Path
from typing import List, Union

from pydantic.schema import schema

from nthp_build.schema import SiteStats


def make_basic_get_operation(
    operation_id: str, tags: List[str], summary: str, model: str
):
    return {
        "get": {
            "operationId": operation_id,
            "tags": tags,
            "summary": summary,
            "parameters": [BRANCH_PARAM],
            "responses": {
                "200": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{model}"}
                        }
                    }
                }
            },
        }
    }


JSON_SCHEMA = schema([SiteStats], title="My Schema")

BRANCH_PARAM = {
    "name": "branch",
    "in": "path",
    "required": True,
    "schema": {
        "type": "string",
    },
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
            "url": "https://nthp-api.wjdp.uk/v1",
            "description": "Production server",
        }
    ],
    "paths": {
        "/{branch}/index.json": make_basic_get_operation(
            operation_id="getSiteStats",
            tags=["site"],
            summary="Get site stats",
            model="SiteStats",
        )
    },
    "components": {"schemas": JSON_SCHEMA["definitions"]},
}


def write_spec(path: Union[str, Path]):
    with open(path, "w") as f:
        json.dump(SPEC, f, indent=4)


if __name__ == "__main__":
    write_spec("openapi.json")
