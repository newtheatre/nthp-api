import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic_collections import BaseCollectionModel


class SmugMugPages(BaseModel):
    Total: int
    Start: int
    Count: int
    RequestedCount: int
    FirstPage: str
    LastPage: str
    NextPage: Optional[str]


class SmugMugResponseInner(BaseModel):
    Uri: str
    Pages: Optional[SmugMugPages]


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
    OriginalSize: Optional[int]
    Processing: bool
    ThumbnailUrl: str
    Title: str
    WebUri: str


class SmugMugImageCollection(BaseCollectionModel[SmugMugImage]):
    pass
