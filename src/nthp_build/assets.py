from enum import Enum
from typing import List, Optional

from nthp_build import models, schema


class AssetType(Enum):
    POSTER = "poster"
    FLYER = "flyer"
    PROGRAMME = "programme"


filter_assets_by_type = lambda assets, type: list(
    filter(lambda asset: asset.type.lower() == type.value, assets)
)


def pick_show_primary_image(assets: List[models.Asset]) -> Optional[str]:
    """Pick an image to use as the primary, to be used in list views &c"""
    image_assets = list(filter(lambda asset: asset.image is not None, assets))
    if override_assets := list(filter(lambda asset: asset.display_image, image_assets)):
        return override_assets[0].image
    if posters := filter_assets_by_type(image_assets, AssetType.POSTER):
        return posters[0].image
    if flyers := filter_assets_by_type(image_assets, AssetType.FLYER):
        return flyers[0].image
    if programmes := filter_assets_by_type(image_assets, AssetType.PROGRAMME):
        return programmes[0].image
    # No suitable image found, oh well we tried
    return None


def get_show_assets(show: models.Show) -> List[schema.Asset]:
    return [schema.Asset(**source_asset.dict()) for source_asset in show.assets]
