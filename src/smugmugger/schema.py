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
    NextPage: str | None


class SmugMugResponseInner(BaseModel):
    Uri: str
    Pages: SmugMugPages | None


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
    OriginalSize: int | None
    Processing: bool
    ThumbnailUrl: str
    Title: str
    WebUri: str


class SmugMugImageCollection(BaseCollectionModel[SmugMugImage]):
    pass
