import asyncio

import httpx
import pytest
from peewee import SqliteDatabase

from nthp_api.smugmugger.client import SmugMugClient
from nthp_api.smugmugger.database import MODELS


@pytest.fixture()
def smug_db():
    smug_db = SqliteDatabase(":memory:")
    with smug_db.bind_ctx(MODELS):
        smug_db.create_tables(MODELS)
        try:
            yield smug_db
        finally:
            smug_db.drop_tables(MODELS)
            smug_db.close()


@pytest.fixture()
def make_mock_client():
    """Build a SmugMugClient serving canned responses from a handler."""

    def _make_mock_client(handler) -> SmugMugClient:
        return SmugMugClient(
            client=httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=True
            ),
            connection_limit=asyncio.Semaphore(1),
        )

    return _make_mock_client
