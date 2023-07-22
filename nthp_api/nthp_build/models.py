"""The models for ingesting data"""

import datetime

from pydantic import BaseModel, root_validator, validator
from pydantic_collections import BaseCollectionModel
from slugify import slugify

from nthp_api.nthp_build import years


class NthpModel(BaseModel):
    class Config:
        frozen = True


class Link(NthpModel):
    type: str
    href: str | None
    snapshot: str | None
    username: str | None
    title: str | None
    date: datetime.date | None
    publisher: str | None
    rating: str | None
    quote: str | None
    note: str | None
    comment: str | None


class Location(NthpModel):
    lat: float
    lon: float


class PersonRef(NthpModel):
    role: str | None
    name: str | None
    note: str | None
    person: bool = True
    comment: str | None


class PersonRole(NthpModel):
    person_id: str | None
    person_name: str | None
    role: str | None
    note: str | None
    is_person: bool = True
    comment: str | None


class ShowCanonical(NthpModel):
    title: str | None
    playwright: str | None


class Asset(NthpModel):
    type: str
    image: str | None
    video: str | None
    filename: str | None
    title: str | None
    page: int | None
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
    def require_title_with_filename(cls, value: str | None, values: dict) -> str | None:
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
    name: str | None
    submitted: datetime.date | None


class Show(NthpModel):
    id: str
    title: str
    playwright: str | None

    devised: str | bool = False

    @validator("devised")
    def handle_devised_strings(cls, value: str | bool) -> str | bool:
        if isinstance(value, str):
            if value.lower() == "true":
                return True
            if value.lower() == "false":
                return False
        return value

    improvised: bool = False
    adaptor: str | None
    translator: str | None
    canonical: list[ShowCanonical] = []
    student_written: bool = False
    company: str | None
    company_sort: str | None
    period: str | None
    season: str
    season_sort: int | None
    venue: str | None
    date_start: datetime.date | None
    date_end: datetime.date | None
    # tour TODO
    trivia: list[Trivia] = []
    cast: list[PersonRef] = []
    crew: list[PersonRef] = []
    cast_incomplete: bool = False
    cast_note: str | None
    crew_incomplete: bool = False
    crew_note: str | None
    prod_shots: str | None
    assets: list[Asset] = []
    links: list[Link] = []
    comment: str | None


class Committee(NthpModel):
    committee: list[PersonRef]


class Venue(NthpModel):
    title: str
    links: list[Link] = []
    built: int | None
    images: list[str] = []
    location: Location | None
    city: str | None = None
    sort: int | None = None
    comment: str | None = None


class Person(NthpModel):
    id: str | None = None
    title: str
    submitted: datetime.date | None = None
    headshot: str | None = None
    # course: List[str] = [] TODO: both lists and strings
    graduated: int | None = None
    award: str | None = None
    # career: Optional[str] TODO: both lists and strings
    links: list[Link] = []
    news: list[Link] = []
    comment: str | None = None


class HistoryRecord(NthpModel):
    year: str
    academic_year: str | None = None
    title: str
    description: str

    @validator("academic_year")
    def require_valid_academic_year(cls, value: str | None) -> str | None:
        if value is not None and not years.check_year_id_is_valid(value):
            raise ValueError("Invalid academic year")
        return value


class HistoryRecordCollection(BaseCollectionModel[HistoryRecord]):
    pass
