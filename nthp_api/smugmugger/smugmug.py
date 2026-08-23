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
    SmugMugAlbumCollection,
    SmugMugImage,
    SmugMugImageCollection,
    SmugMugImageError,
    SmugMugImageInfo,
)

log = logging.getLogger(__name__)

# Albums are cached under their bare key, so everything else needs a namespace.
IMAGE_CACHE_ID_PREFIX = "image:"
USER_ALBUMS_CACHE_ID_PREFIX = "user-albums:"
ALBUM_CACHE_ID_PREFIX = "album:"


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
    if not settings.smugmug_fetch or not settings.smugmug_api_key:
        return SmugMugImageCollection()
    log.info("Fetching album images for %s", album_id)
    album = await nthp_api.smugmugger.album.get_album(client, album_id)
    album_images = await nthp_api.smugmugger.album.get_album_images(client, album_id)
    upsert_cached_album_images(album_id, album, album_images)
    log.info("Fetched album images for %s", album_id)
    return album_images


def get_cached_user_albums(nickname: str) -> SmugMugAlbumCollection | None:
    try:
        cached_result = database.SmugMugResponse.get(
            database.SmugMugResponse.id == USER_ALBUMS_CACHE_ID_PREFIX + nickname
        )
    except peewee.DoesNotExist:
        return None
    return SmugMugAlbumCollection(
        [SmugMugAlbum(**album) for album in json.loads(cached_result.data)]
    )


def upsert_cached_user_albums(nickname: str, albums: SmugMugAlbumCollection) -> None:
    fetched_at = datetime.datetime.now(datetime.UTC)
    database.SmugMugResponse.replace(
        id=USER_ALBUMS_CACHE_ID_PREFIX + nickname,
        last_updated=max((album.LastUpdated for album in albums), default=fetched_at),
        last_fetched=fetched_at,
        data=albums.model_dump_json(),
    ).execute()


async def get_user_albums(
    client: SmugMugClient, nickname: str
) -> SmugMugAlbumCollection:
    """Every album in the account, so the inventory knows the unreferenced ones."""
    if (cached_result := get_cached_user_albums(nickname)) is not None:
        return cached_result
    if not settings.smugmug_fetch or not settings.smugmug_api_key:
        return SmugMugAlbumCollection()
    log.info("Fetching albums for %s", nickname)
    albums = await nthp_api.smugmugger.album.get_user_albums(client, nickname)
    upsert_cached_user_albums(nickname, albums)
    log.info("Fetched %s albums for %s", len(albums), nickname)
    return albums


def get_cached_album(album_id: str) -> SmugMugAlbum | None:
    try:
        cached_result = database.SmugMugResponse.get(
            database.SmugMugResponse.id == ALBUM_CACHE_ID_PREFIX + album_id
        )
    except peewee.DoesNotExist:
        return None
    return SmugMugAlbum(**json.loads(cached_result.data))


def upsert_cached_album(album_id: str, album: SmugMugAlbum) -> None:
    database.SmugMugResponse.replace(
        id=ALBUM_CACHE_ID_PREFIX + album_id,
        last_updated=album.LastUpdated,
        last_fetched=datetime.datetime.now(datetime.UTC),
        data=album.model_dump_json(),
    ).execute()


async def get_album(client: SmugMugClient, album_id: str) -> SmugMugAlbum | None:
    """
    One album by key, for the albums the account sweep does not list.

    The utility albums an editor picks keys out of are reachable by key alone,
    so an album missing from the sweep is asked about rather than given up on.
    """
    if (cached_result := get_cached_album(album_id)) is not None:
        return cached_result
    if not settings.smugmug_fetch or not settings.smugmug_api_key:
        return None
    log.info("Fetching album %s", album_id)
    try:
        album = await nthp_api.smugmugger.album.get_album(client, album_id)
    except SmugMugNotFound:
        log.warning(f"SmugMug has no album {album_id}")
        return None
    upsert_cached_album(album_id, album)
    return album


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


def is_cache_hit(image_info: SmugMugImageInfo) -> bool:
    """
    Whether a cached answer is one worth serving.

    An image SmugMug cannot describe is cached with the reason, so a build only
    ever asks about it once. An entry with neither dimensions nor a reason was
    cached before the reason was recorded, and is asked about again to get one.
    """
    return image_info.has_dimensions or image_info.error is not None


async def get_image_info(client: SmugMugClient, image_key: str) -> SmugMugImageInfo:
    """Dimensions and date for a single image, served from the cache where it can."""
    cached_result = get_cached_image_info(image_key)
    if cached_result is not None and is_cache_hit(cached_result):
        return cached_result
    if not settings.smugmug_fetch or not settings.smugmug_api_key:
        return SmugMugImageInfo()
    log.debug("Fetching image info for %s", image_key)
    try:
        image_info = await nthp_api.smugmugger.image.get_image_info(client, image_key)
    except SmugMugNotFound:
        log.warning(f"SmugMug has no image {image_key}")
        image_info = SmugMugImageInfo(error=SmugMugImageError.NOT_FOUND)
    if not image_info.has_dimensions and image_info.error is None:
        image_info = image_info.model_copy(
            update={"error": SmugMugImageError.NO_DIMENSIONS}
        )
    upsert_cached_image_info(image_key, image_info)
    return image_info


if __name__ == "__main__":
    import asyncio

    async def manual_test():
        async with make_client() as client:
            print(await get_album_images(client, "dvVPZh"))  # noqa: T201

    database.init_db()
    asyncio.run(manual_test())
