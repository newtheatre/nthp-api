"""
The SmugMug inventory the content editors work from.

Editors need to find the key of a file they can see in SmugMug, to know which
images nothing in the archive references, and to know which references SmugMug
cannot answer for. Usage is a fact about the content, so the join between the
account and the content lives here rather than in the site.
"""

import datetime
import json
import logging
from collections import defaultdict

import pydantic

from nthp_api.nthp_build import database, schema
from nthp_api.nthp_build.assets import AssetSource, AssetType
from nthp_api.smugmugger import SmugMugImage, SmugMugImageInfo

log = logging.getLogger(__name__)

ALBUM_ROLE = AssetType.ALBUM.value
TRIVIA_ROLE = "trivia"
NO_DIMENSIONS_REASON = "no_dimensions"

# What an image is to a record that references it by bare key, where the content
# does not say — a person's is their headshot, a venue's a photo of the place.
DEFAULT_ROLES_BY_TARGET_TYPE = {
    "show": "asset",
    "person": "headshot",
    "venue": "photo",
}
DEFAULT_ROLE = "asset"

TargetKey = tuple[str, str]


def get_target_titles() -> dict[TargetKey, str]:
    """What to call each record a reference can point at."""
    titles: dict[TargetKey, str] = {}
    for show in database.Show.select(database.Show.id, database.Show.title):
        titles["show", show.id] = show.title
    for person in database.Person.select(database.Person.id, database.Person.title):
        titles["person", person.id] = person.title
    for venue in database.Venue.select(database.Venue.id, database.Venue.name):
        titles["venue", venue.id] = venue.name
    return titles


def make_asset_use(
    asset: database.Asset, titles: dict[TargetKey, str]
) -> schema.AssetUse:
    target_type = asset.target_type
    if asset.asset_type == AssetType.ALBUM.value:
        role = ALBUM_ROLE
    else:
        role = asset.asset_category or DEFAULT_ROLES_BY_TARGET_TYPE.get(
            target_type, DEFAULT_ROLE
        )
    return schema.AssetUse(
        target_type=target_type,
        target_id=asset.target_id,
        title=titles.get((target_type, asset.target_id), asset.target_id),
        role=role,
    )


def sort_key(use: schema.AssetUse) -> tuple[str, str, str]:
    return use.target_type, use.target_id, use.role


def get_uses_by_key() -> dict[str, list[schema.AssetUse]]:
    """
    Every SmugMug key the content references, and what references it.

    One pass over the assets and the trivia, so a page of a thousand images is a
    thousand dictionary lookups rather than a thousand queries.
    """
    titles = get_target_titles()
    uses: dict[str, list[schema.AssetUse]] = defaultdict(list)
    for asset in database.Asset.select().where(
        database.Asset.asset_source == AssetSource.SMUGMUG.value
    ):
        uses[asset.asset_id].append(make_asset_use(asset, titles))
    for trivia in database.Trivia.select().where(
        database.Trivia.target_image_id.is_null(False)
    ):
        key = database.not_null(trivia.target_image_id)
        targets = {(use.target_type, use.target_id) for use in uses[key]}
        if (trivia.target_type, trivia.target_id) in targets:
            continue
        uses[key].append(
            schema.AssetUse(
                target_type=trivia.target_type,
                target_id=trivia.target_id,
                title=trivia.target_name,
                role=TRIVIA_ROLE,
            )
        )
    return {key: sorted(key_uses, key=sort_key) for key, key_uses in uses.items()}


def get_album_summary(album: database.SmugMugAlbum) -> schema.SmugMugAlbumSummary:
    return schema.SmugMugAlbumSummary(
        key=album.key,
        name=album.name,
        url_name=album.url_name,
        web_uri=album.web_uri,
        image_count=album.image_count,
        last_updated=datetime.datetime.fromisoformat(album.last_updated)
        if album.last_updated
        else None,
    )


def get_album_query():
    return database.SmugMugAlbum.select().order_by(
        database.SmugMugAlbum.name, database.SmugMugAlbum.key
    )


def get_album_inventory(
    uses_by_key: dict[str, list[schema.AssetUse]],
) -> schema.SmugMugAlbumInventoryCollection:
    """Every album in the account, whether the archive references it or not."""
    return schema.SmugMugAlbumInventoryCollection(
        [
            schema.SmugMugAlbumInventory(
                **get_album_summary(album).model_dump(),
                used_by=uses_by_key.get(album.key, []),
            )
            for album in get_album_query()
        ]
    )


def get_album_images(album: database.SmugMugAlbum) -> list[SmugMugImage] | None:
    """The album's images, where the smug step fetched them."""
    if album.images is None:
        return None
    try:
        return [SmugMugImage(**image) for image in json.loads(album.images)]
    except (json.JSONDecodeError, pydantic.ValidationError):
        log.warning(f"Could not decode smugmug data for album {album.key}")
        return None


def get_image_inventory(
    album: database.SmugMugAlbum,
    images: list[SmugMugImage],
    uses_by_key: dict[str, list[schema.AssetUse]],
) -> schema.SmugMugImageInventory:
    return schema.SmugMugImageInventory(
        album=get_album_summary(album),
        images=[
            schema.SmugMugImageInventoryItem(
                key=image.ImageKey,
                file_name=image.FileName,
                title=image.Title or None,
                width=image.OriginalWidth,
                height=image.OriginalHeight,
                is_video=image.IsVideo,
                uploaded_at=image.Date,
                web_uri=image.WebUri,
                used_by=uses_by_key.get(image.ImageKey, []),
            )
            for image in images
        ],
    )


def get_image_info(asset: database.Asset) -> SmugMugImageInfo | None:
    if not asset.asset_smugmug_data:
        return None
    try:
        return SmugMugImageInfo(**json.loads(asset.asset_smugmug_data))
    except (json.JSONDecodeError, pydantic.ValidationError):
        log.warning(f"Could not decode smugmug data for image {asset.asset_id}")
        return None


def get_broken_refs() -> schema.SmugMugBrokenRefCollection:
    """
    Every reference to a key SmugMug could not describe, with why it could not.

    A key the smug step never asked about — a build without an API key, or one
    running from the cache alone — is not a broken reference; it is an unknown one.
    """
    titles = get_target_titles()
    broken = []
    for asset in database.Asset.select().where(
        database.Asset.asset_source == AssetSource.SMUGMUG.value,
        database.Asset.asset_type << [AssetType.IMAGE.value, AssetType.VIDEO.value],
    ):
        image_info = get_image_info(asset)
        if image_info is None or image_info.has_dimensions:
            continue
        reason = image_info.error.value if image_info.error else NO_DIMENSIONS_REASON
        broken.append(
            schema.SmugMugBrokenRef(
                **make_asset_use(asset, titles).model_dump(),
                key=asset.asset_id,
                reason=reason,
            )
        )
    return schema.SmugMugBrokenRefCollection(
        sorted(broken, key=lambda ref: (ref.key, *sort_key(ref)))
    )
