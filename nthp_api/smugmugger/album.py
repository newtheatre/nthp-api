from nthp_api.smugmugger.client import SmugMugClient, get, get_pages
from nthp_api.smugmugger.schema import (
    SmugMugAlbum,
    SmugMugImage,
    SmugMugImageCollection,
)


async def get_album(client: SmugMugClient, album_id: str) -> SmugMugAlbum:
    response = await get(client, f"album/{album_id}")
    return SmugMugAlbum(**response["Response"]["Album"])


async def get_album_images(
    client: SmugMugClient, album_id: str
) -> SmugMugImageCollection:
    images = await get_pages(
        client, f"album/{album_id}!images", response_key="AlbumImage"
    )
    return SmugMugImageCollection([SmugMugImage(**image) for image in images])
