import datetime
import json
import logging

import peewee

import nthp_api.smugmugger.album
import nthp_api.smugmugger.image
from nthp_api.smugmugger import database
from nthp_api.smugmugger.client import SmugMugClient, SmugMugNotFound, make_client
from nthp_api.smugmugger.config import settings
from nthp_api.smugmugger.schema import (
    SmugMugAlbum,
    SmugMugImage,
    SmugMugImageCollection,
    SmugMugImageInfo,
)

log = logging.getLogger(__name__)

# Albums are cached under their bare key, so images need a namespace of their own.
IMAGE_CACHE_ID_PREFIX = "image:"


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
        last_fetched=datetime.datetime.now(datetime.UTC),
        data=album_images.model_dump_json(),
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


def get_cached_image_info(image_key: str) -> SmugMugImageInfo | None:
    try:
        cached_result = database.SmugMugResponse.get(
            database.SmugMugResponse.id == IMAGE_CACHE_ID_PREFIX + image_key
        )
    except peewee.DoesNotExist:
        return None
    return SmugMugImageInfo(**json.loads(cached_result.data))


def upsert_cached_image_info(image_key: str, image_info: SmugMugImageInfo) -> None:
    fetched_at = datetime.datetime.now(datetime.UTC)
    database.SmugMugResponse.replace(
        id=IMAGE_CACHE_ID_PREFIX + image_key,
        last_updated=image_info.date or fetched_at,
        last_fetched=fetched_at,
        data=image_info.model_dump_json(),
    ).execute()


async def get_image_info(client: SmugMugClient, image_key: str) -> SmugMugImageInfo:
    """
    Dimensions and date for a single image, served from the cache where possible.
    An image SmugMug cannot describe is cached as an empty result, so a build only
    ever asks about it once.
    """
    if (cached_result := get_cached_image_info(image_key)) is not None:
        return cached_result
    if not settings.smugmug_fetch:
        return SmugMugImageInfo()
    log.info("Fetching image info for %s", image_key)
    try:
        image_info = await nthp_api.smugmugger.image.get_image_info(client, image_key)
    except SmugMugNotFound:
        log.warning(f"SmugMug has no image {image_key}")
        image_info = SmugMugImageInfo()
    upsert_cached_image_info(image_key, image_info)
    return image_info


if __name__ == "__main__":
    import asyncio

    async def manual_test():
        async with make_client() as client:
            print(await get_album_images(client, "dvVPZh"))  # noqa: T201

    database.init_db()
    asyncio.run(manual_test())
