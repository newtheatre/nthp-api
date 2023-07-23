import json
import logging
import mimetypes
from collections.abc import Generator, Iterable
from enum import Enum

from nthp_api.nthp_build import database, models, schema
from nthp_api.nthp_build.documents import DocumentPath
from nthp_api.smugmugger import SmugMugImage

log = logging.getLogger(__name__)


class AssetTarget(database.DbCompatEnumMixin, Enum):
    SHOW = "show"
    PERSON = "person"
    VENUE = "venue"
    ALBUM = "album"


class AssetSource(database.DbCompatEnumMixin, Enum):
    SMUGMUG = "smugmug"
    FILE = "file"


class AssetType(database.DbCompatEnumMixin, Enum):
    ALBUM = "album"  # A collection of other assets
    IMAGE = "image"  # A single image, a photo or a scanned document
    VIDEO = "video"  # A video
    OTHER = "other"  # A video


class AssetCategory(database.DbCompatEnumMixin, Enum):
    POSTER = "poster"
    FLYER = "flyer"
    PROGRAMME = "programme"
    HEADSHOT = "headshot"


def get_mime_type(source: AssetSource, type: AssetType, id: str) -> str | None:
    """
    Decide or determine the mime-type of an asset.
    :param source: Where does this asset come from?
    :param type: Type of asset
    :param id:
    :return: A mime type, or None if either we can't determine one or one does not apply
    """
    if source is AssetSource.SMUGMUG:
        if type is AssetType.ALBUM:
            return None
        if type is AssetType.IMAGE:
            return "image/jpeg"
        if type is AssetType.VIDEO:
            return "video/mp4"  # TODO: check if correct
        raise ValueError(f"Unhandled asset type {type}")

    if source is AssetSource.FILE:
        guess = mimetypes.guess_type(id)[0]
        if guess is None:
            raise ValueError(f"Could not guess mime type for {id}")
        return guess

    raise ValueError(f"Unhandled asset source {source}")


def save_asset(  # noqa: PLR0913
    target_id: str,
    target_type: AssetTarget,
    source: AssetSource,
    type: AssetType,
    id: str,
    category: AssetCategory | str | None = None,
    title: str | None = None,
    page: int | None = None,
) -> database.Asset:
    return database.Asset.create(
        target_id=target_id,
        target_type=target_type,
        asset_source=source,
        asset_type=type,
        asset_mime_type=get_mime_type(source, type, id),
        asset_id=id,
        asset_category=category,
        title=title,
        page=page,
    )


def assets_from_show_model(
    show: models.Show,
) -> Generator[schema.Asset, None, None]:
    """Generate show assets (output type) from a show model (input type)"""
    for asset in show.assets:
        if asset.image:
            source = AssetSource.SMUGMUG
            type = AssetType.IMAGE
        elif asset.video:
            source = AssetSource.SMUGMUG
            type = AssetType.VIDEO
        elif asset.filename:
            source = AssetSource.FILE
            # We assume files are something else, but could be image or video.
            # In reality they tend to be PDF / audio / other docs
            type = AssetType.OTHER
        else:
            raise ValueError(f"Unhandled mode for asset {asset}")

        asset_id = asset.image or asset.video or asset.filename
        if not asset_id:
            raise ValueError(f"No ID for asset {asset}")

        yield schema.Asset(
            type=str(type),
            source=str(source),
            mime_type=get_mime_type(source, type, asset_id),
            id=asset_id,
            category=asset.type,
            # we use type for image/video/other, source uses it for category
            title=asset.title,
            page=asset.page,
        )

    if show.prod_shots:
        yield schema.Asset(
            type=str(AssetType.ALBUM),
            source=str(AssetSource.SMUGMUG),
            mime_type=get_mime_type(
                AssetSource.SMUGMUG, AssetType.ALBUM, show.prod_shots
            ),
            id=show.prod_shots,
        )


def save_show_assets(
    path: DocumentPath, show_assets: Iterable[schema.Asset]
) -> list[database.Asset]:
    """Write assets to the database"""
    return [
        save_asset(
            target_id=path.id,
            target_type=AssetTarget.SHOW,
            source=AssetSource(asset.source),
            type=AssetType(asset.type),
            id=asset.id,
            category=asset.category,
            title=asset.title,
            page=asset.page,
        )
        for asset in show_assets
    ]


def save_person_assets(
    path: DocumentPath, person: models.Person
) -> list[database.Asset]:
    assets = []
    if person.headshot:
        assets.append(
            save_asset(
                target_id=path.id,
                target_type=AssetTarget.PERSON,
                source=AssetSource.SMUGMUG,
                type=AssetType.IMAGE,
                id=person.headshot,
                category=AssetCategory.HEADSHOT,
                title=person.title,
            )
        )
    return assets


def filter_assets_by_type(assets, type):
    return list(filter(lambda asset: asset.type.lower() == type.value, assets))


def pick_show_primary_image(assets: list[models.Asset]) -> str | None:
    """
    Pick an image to use as the primary, to be used in list views &c
    TODO: Currently we return a SmugMug ID rather than a full Asset object.
    """
    image_assets = list(filter(lambda asset: asset.image is not None, assets))
    if override_assets := list(filter(lambda asset: asset.display_image, image_assets)):
        return override_assets[0].image
    if posters := filter_assets_by_type(image_assets, AssetCategory.POSTER):
        return posters[0].image
    if flyers := filter_assets_by_type(image_assets, AssetCategory.FLYER):
        return flyers[0].image
    if programmes := filter_assets_by_type(image_assets, AssetCategory.PROGRAMME):
        return programmes[0].image
    # No suitable image found, oh well we tried
    return None


def smugmug_asset_to_asset(smugmug_asset: SmugMugImage) -> schema.Asset:
    """Convert a SmugMug asset to a schema asset"""
    asset_type = AssetType.VIDEO if smugmug_asset.IsVideo else AssetType.IMAGE
    return schema.Asset(
        id=smugmug_asset.ImageKey,
        source=AssetSource.SMUGMUG.value,
        title=smugmug_asset.Title or None,
        type=asset_type.value,
        mime_type=get_mime_type(
            AssetSource.SMUGMUG, asset_type, smugmug_asset.ImageKey
        ),
    )


def get_asset_collection_from_album(
    album: database.Asset,
) -> schema.AssetCollection | None:
    """
    Get AssetCollection from an asset album.
    Currently, we only support SmugMug albums.
    If the SmugMug data isn't present or fails to parse, we return None.
    """
    if album.asset_source != AssetSource.SMUGMUG.value:
        raise ValueError(f"Album source '{album.asset_source}' unsupported")
    if not album.asset_smugmug_data:
        log.warning(f"No smugmug data for album {album.asset_id}")
        return None
    try:
        smugmug_album_images = json.loads(album.asset_smugmug_data)
        smugmug_assets = [SmugMugImage(**asset) for asset in smugmug_album_images]
    except json.JSONDecodeError:
        log.warning(f"Could not decode smugmug data for album {album.asset_id}")
        return None
    return schema.AssetCollection(
        [smugmug_asset_to_asset(asset) for asset in smugmug_assets]
    )
