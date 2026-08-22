"""Fetching a single image by key, for assets referenced outside an album."""

import logging

from nthp_api.smugmugger.client import SmugMugClient, get
from nthp_api.smugmugger.schema import (
    SmugMugImageDetail,
    SmugMugImageInfo,
    SmugMugImageSizeDetails,
)

log = logging.getLogger(__name__)


async def get_image(client: SmugMugClient, image_key: str) -> SmugMugImageDetail:
    response = await get(client, f"image/{image_key}")
    return SmugMugImageDetail(**response["Response"]["Image"])


async def get_image_size_details(
    client: SmugMugClient, image_key: str
) -> SmugMugImageSizeDetails:
    response = await get(client, f"image/{image_key}!sizedetails")
    return SmugMugImageSizeDetails(**response["Response"]["ImageSizeDetails"])


async def get_image_info(client: SmugMugClient, image_key: str) -> SmugMugImageInfo:
    """
    Dimensions and date for an image key.
    The image endpoint carries both in one request; where it omits the dimensions
    we fall back to the size details endpoint, which always knows them.
    """
    image = await get_image(client, image_key)
    info = SmugMugImageInfo(
        width=image.OriginalWidth, height=image.OriginalHeight, date=image.Date
    )
    if info.has_dimensions:
        return info
    size_details = await get_image_size_details(client, image_key)
    size = size_details.ImageSizeOriginal or size_details.ImageSizeLarge
    if size is None:
        log.warning(f"No original size for image {image_key}")
        return info
    return info.model_copy(update={"width": size.Width, "height": size.Height})
