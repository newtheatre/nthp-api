"""The models for ingesting data"""

from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    model_validator,
)
from pydantic_collections import BaseCollectionModel
from slugify import slugify

from nthp_api.nthp_build import years
from nthp_api.nthp_build.fields import FuzzyDate, PermissiveStr


class NthpModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class Link(NthpModel):
    type: str
    href: str | None = None
    snapshot: str | None = None
    username: PermissiveStr | None = None
    title: PermissiveStr | None = None
    date: FuzzyDate | None = None
    publisher: PermissiveStr | None = None
    rating: PermissiveStr | None = None
    quote: PermissiveStr | None = None
    note: PermissiveStr | None = None
    comment: PermissiveStr | None = None


class Award(str, Enum):
    """An award made to a person on leaving the theatre."""

    FELLOWSHIP = "Fellowship"
    COMMENDATION = "Commendation"
    MERIT = "Merit"
    UNION_PRIZE = "Union Prize"


class Location(NthpModel):
    lat: float
    lon: float


class PersonRef(NthpModel):
    role: PermissiveStr | None = None
    name: str | None = None
    note: PermissiveStr | None = None
    person: bool = True
    comment: PermissiveStr | None = None


class PersonRole(NthpModel):
    person_id: str | None = None
    person_name: str | None = None
    role: PermissiveStr | None = None
    note: PermissiveStr | None = None
    is_person: bool = True
    comment: PermissiveStr | None = None


class ShowCanonical(NthpModel):
    title: PermissiveStr | None = None
    playwright: str | None = None


class Asset(NthpModel):
    type: str
    image: str | None = None
    video: str | None = None
    filename: str | None = None
    title: PermissiveStr | None = None
    page: int | None = None
    display_image: bool = False

    @model_validator(mode="before")
    @classmethod
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

    @field_validator("type")
    @classmethod
    def slugify_type(cls, value: str) -> str:
        return slugify(value)

    @model_validator(mode="after")
    def require_title_with_filename(self) -> "Asset":
        if self.filename is not None and self.title is None:
            raise ValueError("title is required if filename is provided")
        return self

    @model_validator(mode="after")
    def display_image_only_for_images(self) -> "Asset":
        if self.display_image and not self.image:
            raise ValueError("Can only set display_image for images")
        return self


class Trivia(NthpModel):
    quote: str
    name: str | None = None
    submitted: FuzzyDate | None = None


class TourDate(NthpModel):
    venue: PermissiveStr | None = None
    date_start: FuzzyDate | None = None
    date_end: FuzzyDate | None = None
    note: PermissiveStr | None = None
    comment: PermissiveStr | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_notes_alias(cls, values: dict) -> dict:
        if isinstance(values, dict) and "notes" in values:
            values = {**values, "note": values.pop("notes")}
        return values


class Show(NthpModel):
    id: str
    title: str
    playwright: str | None = None

    devised: str | bool = False

    @field_validator("devised")
    @classmethod
    def handle_devised_strings(cls, value: str | bool) -> str | bool:
        if isinstance(value, str):
            if value.lower() == "true":
                return True
            if value.lower() == "false":
                return False
        return value

    improvised: bool = False
    adaptor: str | None = None
    translator: str | None = None
    canonical: list[ShowCanonical] = []
    student_written: bool = False
    company: PermissiveStr | None = None
    company_sort: PermissiveStr | None = None
    period: str | None = None
    season: str
    season_sort: int | None = None
    venue: PermissiveStr | None = None
    venue_sort: PermissiveStr | None = None
    date_start: FuzzyDate | None = None
    date_end: FuzzyDate | None = None
    tour: list[TourDate] = []
    trivia: list[Trivia] = []
    cast: list[PersonRef] = []
    crew: list[PersonRef] = []
    cast_incomplete: bool = False
    cast_note: PermissiveStr | None = None
    crew_incomplete: bool = False
    crew_note: PermissiveStr | None = None
    ignore_missing: bool = False
    prod_shots: str | None = None
    assets: list[Asset] = []
    links: list[Link] = []
    comment: PermissiveStr | None = None


class Committee(NthpModel):
    committee: list[PersonRef]


class Venue(NthpModel):
    title: str
    links: list[Link] = []
    built: int | None = None
    images: list[str] = []
    location: Location | None = None
    city: str | None = None
    sort: int | None = None
    comment: PermissiveStr | None = None


class Person(NthpModel):
    id: str | None = None
    title: str
    submitted: FuzzyDate | bool | None = None
    headshot: str | None = None
    course: list[PermissiveStr] = []
    graduated: int | None = None
    award: Award | None = None
    careers: list[PermissiveStr] = []
    links: list[Link] = []
    news: list[Link] = []
    comment: PermissiveStr | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_career_alias(cls, values: dict) -> dict:
        """Most records use `careers`, a couple use `career`."""
        if isinstance(values, dict) and "career" in values:
            values = {**values, "careers": values.pop("career")}
        return values

    @field_validator("course", "careers", mode="before")
    @classmethod
    def coerce_to_list(cls, value: object) -> object:
        """Both fields are authored as either a single value or a list of them."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @field_validator("award", mode="before")
    @classmethod
    def blank_award_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class HistoryRecord(NthpModel):
    year: PermissiveStr
    academic_year: str | None = None
    title: str
    description: str

    @field_validator("academic_year")
    @classmethod
    def require_valid_academic_year(cls, value: str | None) -> str | None:
        if value is not None and not years.check_source_year_id_is_valid(value):
            raise ValueError("Invalid academic year")
        return value


class HistoryRecordCollection(BaseCollectionModel[HistoryRecord]):
    pass


class CrewRoleDefinition(NthpModel):
    """
    A crew role as defined by the content repo's `_data/roles.yaml`.

    Icons and the `show` flag are presentation concerns and are ignored.
    """

    role: str
    aliases: list[str] = []

    @field_validator("role", "aliases", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        """Names in roles.yaml carry trailing whitespace."""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            return [item.strip() if isinstance(item, str) else item for item in value]
        return value


class CrewRoleDefinitionCollection(BaseCollectionModel[CrewRoleDefinition]):
    pass


class LinkTypeDefinition(NthpModel):
    """
    A link type as defined by the content repo's `_data/link-types.yaml`.

    Icons and proofer flags are presentation concerns and are ignored.
    """

    type: str
    href: str | None = None
    is_news: bool = False

    @field_validator("type", "href", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        """Types in link-types.yaml carry trailing whitespace."""
        if isinstance(value, str):
            return value.strip()
        return value


class LinkTypeDefinitionCollection(BaseCollectionModel[LinkTypeDefinition]):
    pass
