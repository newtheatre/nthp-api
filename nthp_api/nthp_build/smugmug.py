import asyncio
import logging

from nthp_api import smugmugger
from nthp_api.nthp_build import database
from nthp_api.nthp_build.assets import AssetSource, AssetType

log = logging.getLogger(__name__)


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
    many assets share it. Keys SmugMug cannot describe are left without data, so
    the API emits nulls for them.
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
        if image_info is None or not image_info.has_dimensions:
            log.warning(f"No dimensions for image {asset.asset_id}")
            continue
        asset.asset_smugmug_data = image_info.model_dump_json()
        asset.save()
        updated_count += 1
    return updated_count


async def async_main():
    async with smugmugger.make_client() as client:
        albums = get_albums_to_fetch()

        assets_to_update = await asyncio.gather(
            *[update_album(client, asset) for asset in albums]
        )

        log.info(f"Writing {len(assets_to_update)} assets (albums) to db")

        updated_image_count = await update_images(client)
        log.info(f"Wrote {updated_image_count} assets (images) to db")


def run():
    asyncio.run(async_main())
