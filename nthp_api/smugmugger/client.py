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
        # A bare image key redirects to its serial-suffixed canonical URI.
        client=httpx.AsyncClient(
            timeout=settings.smugmug_timeout_seconds, follow_redirects=True
        ),
        connection_limit=asyncio.Semaphore(settings.smugmug_connection_limit),
    )
    yield client
    await client.client.aclose()


RETRYABLE_STATUS_CODES = frozenset(
    {
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    }
)


def get_retry_after_seconds(response: httpx.Response) -> float | None:
    """Seconds SmugMug asks us to wait, if it says so in a form we understand."""
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return float(retry_after)
    except ValueError:
        log.warning(f"Ignoring unparseable Retry-After header {retry_after!r}")
        return None


async def _get_with_retry(
    client: SmugMugClient, url: str, params: dict
) -> httpx.Response:
    last_exc: Exception | None = None
    last_response: httpx.Response | None = None
    retry_after_seconds: float | None = None
    for attempt in range(settings.smugmug_retry_attempts):
        if attempt:
            delay = retry_after_seconds or (
                settings.smugmug_retry_backoff_seconds * 2 ** (attempt - 1)
            )
            reason = last_exc if last_exc is not None else last_response
            log.warning(
                f"Retrying {url} in {delay}s "
                f"(attempt {attempt + 1}/{settings.smugmug_retry_attempts}): "
                f"{reason!r}"
            )
            await asyncio.sleep(delay)
        try:
            async with client.connection_limit:
                response = await client.client.get(
                    url, params=params, headers={"Accept": "application/json"}
                )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc, last_response, retry_after_seconds = exc, None, None
            continue
        if response.status_code not in RETRYABLE_STATUS_CODES:
            return response
        last_exc, last_response = None, response
        retry_after_seconds = get_retry_after_seconds(response)
    if last_response is not None:
        return last_response
    assert last_exc is not None
    raise last_exc


async def get(client: SmugMugClient, url, params=None):
    if not settings.smugmug_api_key:
        raise ConfigError("No SmugMug API key configured")
    if params is None:
        params = {}
    params["APIKey"] = settings.smugmug_api_key
    response = await _get_with_retry(client, make_url(url), params)
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
