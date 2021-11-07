import datetime
import json
import logging
from typing import Optional

import peewee

import smugmugger.album
from smugmugger import database
from smugmugger.client import SmugMugClient, make_client
from smugmugger.config import settings
from smugmugger.schema import SmugMugImage, SmugMugImageCollection

log = logging.getLogger(__name__)


def get_cached_album_images(album_id: str) -> Optional[SmugMugImageCollection]:
    try:
        cached_result = database.SmugMugResponse.get(
            database.SmugMugResponse.id == album_id
        )
        return SmugMugImageCollection(
            [SmugMugImage(**image) for image in json.loads(cached_result.data)]
        )
    except peewee.DoesNotExist:
        return None


async def get_album_images(
    client: SmugMugClient, album_id: str
) -> SmugMugImageCollection:
    if cached_result := get_cached_album_images(album_id):
        return cached_result
    if not settings.smugmug_fetch:
        return SmugMugImageCollection()
    log.info("Fetching album images for %s", album_id)
    album = await smugmugger.album.get_album(client, album_id)
    album_images = await smugmugger.album.get_album_images(client, album_id)
    database.SmugMugResponse.create(
        id=album_id,
        last_updated=album.ImagesLastUpdated,
        last_fetched=datetime.datetime.now(),
        data=album_images.json(),
    )
    return album_images


if __name__ == "__main__":
    import asyncio

    async def manual_test():
        async with make_client() as client:
            print(await get_album_images(client, "dvVPZh"))

    database.init_db()
    asyncio.run(manual_test())
