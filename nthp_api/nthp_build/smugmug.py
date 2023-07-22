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


async def update_album(client: smugmugger.SmugMugClient, asset: database.Asset):
    log.debug(f"Updating {asset.asset_id}")
    image_collection = await smugmugger.get_album_images(client, asset.asset_id)
    asset.asset_smugmug_data = image_collection.json(
        exclude_unset=True, exclude_none=True
    )
    asset.save()
    return asset


async def async_main():
    async with smugmugger.make_client() as client:
        albums = get_albums_to_fetch()

        assets_to_update = await asyncio.gather(
            *[update_album(client, asset) for asset in albums]
        )

        log.info(f"Writing {len(assets_to_update)} assets (albums) to db")


def run():
    asyncio.run(async_main())
