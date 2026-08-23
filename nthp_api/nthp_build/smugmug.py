import asyncio
import logging

from nthp_api import smugmugger
from nthp_api.nthp_build import database
from nthp_api.nthp_build.assets import AssetSource, AssetType
from nthp_api.nthp_build.config import settings
from nthp_api.smugmugger.config import settings as smugmugger_settings

log = logging.getLogger(__name__)


def fetch_enabled() -> bool:
    return bool(
        smugmugger_settings.smugmug_fetch and smugmugger_settings.smugmug_api_key
    )


def get_albums_to_fetch():
    return database.Asset.select().where(
        database.Asset.asset_source == AssetSource.SMUGMUG,
        database.Asset.asset_type == AssetType.ALBUM,
    )


def get_images_to_fetch():
    """Assets referenced by a bare SmugMug key: posters, headshots and the like."""
    return database.Asset.select().where(
        database.Asset.asset_source == AssetSource.SMUGMUG,
        database.Asset.asset_type << [AssetType.IMAGE, AssetType.VIDEO],
    )


def get_referenced_album_keys() -> set[str]:
    return {asset.asset_id for asset in get_albums_to_fetch()}


async def update_album(client: smugmugger.SmugMugClient, asset: database.Asset):
    log.debug(f"Updating {asset.asset_id}")
    image_collection = await smugmugger.get_album_images(client, asset.asset_id)
    asset.asset_smugmug_data = image_collection.model_dump_json(
        exclude_unset=True, exclude_none=True
    )
    asset.save()
    return asset


async def fetch_image_info(
    client: smugmugger.SmugMugClient, image_key: str
) -> tuple[str, smugmugger.SmugMugImageInfo | None]:
    try:
        return image_key, await smugmugger.get_image_info(client, image_key)
    except Exception:
        log.exception(f"Failed to fetch image info for {image_key}")
        return image_key, None


async def update_images(client: smugmugger.SmugMugClient) -> int:
    """
    Give every bare-key image asset its dimensions, fetching each key once however
    many assets share it. A key SmugMug cannot describe is recorded with the reason
    instead, so the API emits nulls for it and the editor inventory reports it.
    """
    image_assets = list(get_images_to_fetch())
    image_keys = sorted({asset.asset_id for asset in image_assets})
    log.info(f"Fetching info for {len(image_keys)} images")
    results = dict(
        await asyncio.gather(*[fetch_image_info(client, key) for key in image_keys])
    )

    updated_count = 0
    for asset in image_assets:
        image_info = results[asset.asset_id]
        if image_info is None:
            image_info = smugmugger.SmugMugImageInfo(
                error=smugmugger.SmugMugImageError.FETCH_FAILED
            )
        elif not image_info.has_dimensions and image_info.error is None:
            # Never asked about: no API key, or fetching off and nothing cached.
            continue
        asset.asset_smugmug_data = image_info.model_dump_json()
        asset.save()
        if image_info.has_dimensions:
            updated_count += 1
        elif fetch_enabled():
            log.debug(f"No dimensions for image {asset.asset_id}")
    return updated_count


def make_album_row(
    album: smugmugger.SmugMugAlbum, images: smugmugger.SmugMugImageCollection | None
) -> dict:
    return {
        "key": album.AlbumKey,
        "name": album.Name,
        "url_name": album.UrlName,
        "web_uri": album.WebUri,
        "image_count": album.ImageCount,
        "last_updated": album.LastUpdated.isoformat(),
        "images": images.model_dump_json() if images is not None else None,
    }


async def update_album_inventory(client: smugmugger.SmugMugClient) -> int:
    """
    Record every album we know of, so the inventory can name the unused ones.

    The account sweep lists the production shot albums; the utility albums an
    editor picks keys out of are not listed and are asked about by key. Images
    are fetched only for those and for the albums a show references; the rest
    are listed by name and count alone.
    """
    albums_by_key = {
        album.AlbumKey: album
        for album in await smugmugger.get_user_albums(
            client, smugmugger_settings.smugmug_nickname
        )
    }
    keys_with_images = set(settings.smugmug_utility_album_keys) | (
        get_referenced_album_keys()
    )
    for key in sorted(keys_with_images - set(albums_by_key)):
        album = await smugmugger.get_album(client, key)
        if album is not None:
            albums_by_key[key] = album

    if not albums_by_key:
        if fetch_enabled():
            log.warning("No SmugMug albums found; album inventory will be empty")
        return 0

    rows = [
        make_album_row(
            album,
            await smugmugger.get_album_images(client, key)
            if key in keys_with_images
            else None,
        )
        for key, album in albums_by_key.items()
    ]
    database.SmugMugAlbum.replace_many(rows).execute()
    return len(rows)


async def async_main():
    if not fetch_enabled() and smugmugger_settings.smugmug_fetch:
        log.warning(
            "No SmugMug API key configured; skipping image fetch — image "
            "dimensions and album data will be omitted"
        )

    async with smugmugger.make_client() as client:
        albums = get_albums_to_fetch()

        assets_to_update = await asyncio.gather(
            *[update_album(client, asset) for asset in albums]
        )

        log.info(f"Writing {len(assets_to_update)} assets (albums) to db")

        updated_image_count = await update_images(client)
        log.info(f"Wrote {updated_image_count} assets (images) to db")

        album_count = await update_album_inventory(client)
        log.info(f"Wrote {album_count} albums (inventory) to db")


def run():
    asyncio.run(async_main())
