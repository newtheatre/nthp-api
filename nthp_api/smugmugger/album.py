from nthp_api.smugmugger.client import SmugMugClient, get, get_pages
from nthp_api.smugmugger.schema import (
    SmugMugAlbum,
    SmugMugAlbumCollection,
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


async def get_user_albums(
    client: SmugMugClient, nickname: str
) -> SmugMugAlbumCollection:
    """Every album in an account, however many pages SmugMug spreads them over."""
    albums = await get_pages(client, f"user/{nickname}!albums", response_key="Album")
    return SmugMugAlbumCollection([SmugMugAlbum(**album) for album in albums])
