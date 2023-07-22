import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from http import HTTPStatus
from typing import NamedTuple

import httpx

from nthp_api.smugmugger import schema
from nthp_api.smugmugger.config import settings

log = logging.getLogger(__name__)
PAGE_SIZE = 100


class ConfigError(Exception):
    pass


class SmugMugApiError(Exception):
    pass


class SmugMugNotFound(Exception):
    pass


class SmugMugInvalidResponse(Exception):
    pass


def make_url(path: str) -> str:
    return "https://api.smugmug.com/api/v2/" + path


class SmugMugClient(NamedTuple):
    client: httpx.AsyncClient
    connection_limit: asyncio.Semaphore


@contextlib.asynccontextmanager
async def make_client() -> AsyncGenerator[SmugMugClient, None]:
    client = SmugMugClient(
        client=httpx.AsyncClient(),
        connection_limit=asyncio.Semaphore(settings.smugmug_connection_limit),
    )
    yield client
    await client.client.aclose()


async def get(client: SmugMugClient, url, params=None):
    if not settings.smugmug_api_key:
        raise ConfigError("No SmugMug API key configured")
    if params is None:
        params = {}
    params["APIKey"] = settings.smugmug_api_key
    async with client.connection_limit:
        response = await client.client.get(
            make_url(url), params=params, headers={"Accept": "application/json"}
        )
    try:
        data = response.json()
    except ValueError as e:
        log.exception(response.text)
        raise SmugMugInvalidResponse from e
    response_obj = schema.SmugMugResponse(**data)
    if not response.is_success:
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise SmugMugNotFound(response_obj.Message)
        raise SmugMugApiError(response_obj.Message)
    return data


async def get_pages(
    client: SmugMugClient, url: str, response_key: str, params: dict | None = None
):
    """
    Fetch all items from a collection by iterating over pages.
    """
    if not params:
        params = {}
    start = 1
    wanted_data = []
    while True:
        params["start"] = start
        params["count"] = PAGE_SIZE
        data = await get(client, url, params=params)
        response = schema.SmugMugResponse(**data)
        assert response.Response.Pages is not None, "No Pages object in response"
        pages = response.Response.Pages
        assert pages.RequestedCount == PAGE_SIZE
        wanted_data.extend(data["Response"][response_key])
        if not pages.NextPage:
            break
        start += PAGE_SIZE
    return wanted_data
