import datetime
import json
import logging

import peewee

import nthp_api.smugmugger.album
from nthp_api.smugmugger import database
from nthp_api.smugmugger.client import SmugMugClient, make_client
from nthp_api.smugmugger.config import settings
from nthp_api.smugmugger.schema import (
    SmugMugAlbum,
    SmugMugImage,
    SmugMugImageCollection,
)

log = logging.getLogger(__name__)


def get_cached_album_images(album_id: str) -> SmugMugImageCollection | None:
    try:
        cached_result = database.SmugMugResponse.get(
            database.SmugMugResponse.id == album_id
        )
        return SmugMugImageCollection(
            [SmugMugImage(**image) for image in json.loads(cached_result.data)]
        )
    except peewee.DoesNotExist:
        return None


def upsert_cached_album_images(
    album_id: str, album: SmugMugAlbum, album_images: SmugMugImageCollection
):
    """Either create or update cache for an album's images."""
    database.SmugMugResponse.replace(
        id=album_id,
        last_updated=album.ImagesLastUpdated,
        last_fetched=datetime.datetime.now(),
        data=album_images.json(),
    ).execute()


async def get_album_images(
    client: SmugMugClient, album_id: str
) -> SmugMugImageCollection:
    if cached_result := get_cached_album_images(album_id):
        return cached_result
    if not settings.smugmug_fetch:
        return SmugMugImageCollection()
    log.info("Fetching album images for %s", album_id)
    album = await nthp_api.smugmugger.album.get_album(client, album_id)
    album_images = await nthp_api.smugmugger.album.get_album_images(client, album_id)
    upsert_cached_album_images(album_id, album, album_images)
    log.info("Fetched album images for %s", album_id)
    return album_images


if __name__ == "__main__":
    import asyncio

    async def manual_test():
        async with make_client() as client:
            print(await get_album_images(client, "dvVPZh"))  # noqa: T201

    database.init_db()
    asyncio.run(manual_test())
