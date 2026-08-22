import datetime

from pydantic import BaseModel
from pydantic_collections import BaseCollectionModel


class SmugMugPages(BaseModel):
    Total: int
    Start: int
    Count: int
    RequestedCount: int
    FirstPage: str
    LastPage: str
    NextPage: str | None = None


class SmugMugResponseInner(BaseModel):
    Uri: str
    Pages: SmugMugPages | None = None


class SmugMugResponse(BaseModel):
    Code: int
    Message: str
    Response: SmugMugResponseInner


class SmugMugAlbum(BaseModel):
    """https://api.smugmug.com/api/v2/doc/reference/album.html"""

    Uri: str
    AlbumKey: str
    ImagesLastUpdated: datetime.datetime
    LastUpdated: datetime.datetime
    Name: str
    NiceName: str


class SmugMugImage(BaseModel):
    """https://api.smugmug.com/api/v2/doc/reference/album-image.html"""

    Uri: str
    Date: datetime.datetime
    FileName: str
    Format: str
    ImageKey: str
    IsVideo: bool
    OriginalHeight: int
    OriginalWidth: int
    OriginalSize: int | None = None
    Processing: bool
    ThumbnailUrl: str
    Title: str
    WebUri: str


class SmugMugImageCollection(BaseCollectionModel[SmugMugImage]):
    pass


class SmugMugImageSize(BaseModel):
    Width: int
    Height: int


class SmugMugImageSizeDetails(BaseModel):
    """https://api.smugmug.com/api/v2/doc/reference/image-sizes.html"""

    ImageSizeOriginal: SmugMugImageSize | None = None
    ImageSizeLarge: SmugMugImageSize | None = None


class SmugMugImageDetail(BaseModel):
    """
    https://api.smugmug.com/api/v2/doc/reference/image.html
    A standalone image, fetched by key. Unlike an album image the fields we want
    are not guaranteed to be present, so all are optional.
    """

    ImageKey: str
    Date: datetime.datetime | None = None
    OriginalHeight: int | None = None
    OriginalWidth: int | None = None


class SmugMugImageInfo(BaseModel):
    """The intrinsic dimensions and upload date of an image, however we found them."""

    width: int | None = None
    height: int | None = None
    date: datetime.datetime | None = None

    @property
    def has_dimensions(self) -> bool:
        return self.width is not None and self.height is not None
