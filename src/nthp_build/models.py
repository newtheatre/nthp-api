"""The models for ingesting data"""

import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, root_validator, validator
from pydantic_collections import BaseCollectionModel
from slugify import slugify

from nthp_build import years


class NthpModel(BaseModel):
    class Config:
        frozen = True


class Link(NthpModel):
    type: str
    href: Optional[str]
    snapshot: Optional[str]
    username: Optional[str]
    title: Optional[str]
    date: Optional[datetime.date]
    publisher: Optional[str]
    rating: Optional[str]
    quote: Optional[str]
    note: Optional[str]
    comment: Optional[str]


class Location(NthpModel):
    lat: float
    lon: float


class PersonRef(NthpModel):
    role: Optional[str]
    name: Optional[str]
    note: Optional[str]
    person: bool = True
    comment: Optional[str]


class PersonRole(NthpModel):
    person_id: Optional[str]
    person_name: Optional[str]
    role: Optional[str]
    note: Optional[str]
    is_person: bool = True
    comment: Optional[str]


class ShowCanonical(NthpModel):
    title: Optional[str]
    playwright: Optional[str]


class Asset(NthpModel):
    type: str
    image: Optional[str]
    video: Optional[str]
    filename: Optional[str]
    title: Optional[str]
    page: Optional[int]
    display_image: bool = False

    @root_validator()
    def require_image_xor_video_xor_filename(cls, values: dict) -> dict:
        if (
            sum(
                (
                    1 if values.get("image") else 0,
                    1 if values.get("video") else 0,
                    1 if values.get("filename") else 0,
                )
            )
            != 1
        ):
            raise ValueError("Must have exactly one of image, video, or filename")
        return values

    @validator("type")
    def slugify_type(cls, value: str) -> str:
        return slugify(value)

    @validator("title", always=True)
    def require_title_with_filename(
        cls, value: Optional[str], values: dict
    ) -> Optional[str]:
        if values.get("filename") is not None and value is None:
            raise ValueError("title is required if filename is provided")
        return value

    @validator("display_image")
    def display_image_only_for_images(cls, value: bool, values: dict) -> bool:
        if value and not values.get("image"):
            raise ValueError("Can only set display_image for images")
        return value


class Trivia(NthpModel):
    quote: str
    name: Optional[str]
    submitted: Optional[datetime.date]


class Show(NthpModel):
    id: str
    title: str
    playwright: Optional[str]

    devised: Union[str, bool] = False

    @validator("devised")
    def handle_devised_strings(cls, value: Union[str, bool]) -> Union[str, bool]:
        if isinstance(value, str):
            if value.lower() == "true":
                return True
            elif value.lower() == "false":
                return False
        return value

    improvised: bool = False
    adaptor: Optional[str]
    translator: Optional[str]
    canonical: List[ShowCanonical] = []
    student_written: bool = False
    company: Optional[str]
    company_sort: Optional[str]
    period: Optional[str]
    season: str
    season_sort: Optional[int]
    venue: Optional[str]
    date_start: Optional[datetime.date]
    date_end: Optional[datetime.date]
    # tour TODO
    trivia: List[Trivia] = []
    cast: List[PersonRef] = []
    crew: List[PersonRef] = []
    cast_incomplete: bool = False
    cast_note: Optional[str]
    crew_incomplete: bool = False
    crew_note: Optional[str]
    prod_shots: Optional[str]
    assets: List[Asset] = []
    links: List[Link] = []
    comment: Optional[str]


class Committee(NthpModel):
    committee: List[PersonRef]


class Venue(NthpModel):
    title: str
    links: List[Link] = []
    built: Optional[int]
    images: List[str] = []
    location: Optional[Location]
    city: Optional[str] = None
    sort: Optional[int] = None
    comment: Optional[str] = None


class Person(NthpModel):
    id: Optional[str] = None
    title: str
    submitted: Optional[datetime.date] = None
    headshot: Optional[str] = None
    # course: List[str] = [] TODO: both lists and strings
    graduated: Optional[int] = None
    award: Optional[str] = None
    # career: Optional[str] TODO: both lists and strings
    links: List[Link] = []
    news: List[Link] = []
    comment: Optional[str] = None


class HistoryRecord(NthpModel):
    year: str
    academic_year: Optional[str] = None
    title: str
    description: str

    @validator("academic_year")
    def require_valid_academic_year(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not years.check_year_id_is_valid(value):
            raise ValueError("Invalid academic year")
        return value


class HistoryRecordCollection(BaseCollectionModel[HistoryRecord]):
    pass
