"""The schema for outputting data"""

import datetime
from enum import Enum

import humps
from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import ComputedFieldInfo, FieldInfo
from pydantic_collections import BaseCollectionModel

from nthp_api.nthp_build import models, years
from nthp_api.nthp_build.fields import FuzzyDate, PermissiveStr


def field_title(field_name: str, _field_info: FieldInfo | ComputedFieldInfo) -> str:
    return field_name.replace("_", " ").title()


RESPONSE_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=humps.camelize,
    field_title_generator=field_title,
    frozen=True,
)


class NthpSchema(BaseModel):
    model_config = RESPONSE_CONFIG


class Location(NthpSchema):
    lat: float
    lon: float

    @classmethod
    def from_model(cls, model: models.Location):
        return cls(lat=model.lat, lon=model.lon)


class PersonRoleList(models.PersonRole):
    model_config = RESPONSE_CONFIG


class PersonList(NthpSchema):
    id: str
    name: str | None = None
    is_person: bool
    headshot: str | None = None
    has_bio: bool


class PlayShow(NthpSchema):
    id: str
    title: str


class PlaywrightType(Enum):
    PLAYWRIGHT = "playwright"
    VARIOUS = "various"
    UNKNOWN = "unknown"
    DEVISED = "devised"
    IMPROVISED = "improvised"


class Playwright(NthpSchema):
    id: str | None = None
    name: str | None = None
    person_id: str | None = None


class PlaywrightShow(Playwright):
    type: PlaywrightType
    descriptor: str | None = None
    student_written: bool


class ShowRole(NthpSchema):
    role: str | None = None
    person: PersonList | None = None
    note: str | None = None


class Asset(NthpSchema):
    type: str
    source: str
    id: str
    mime_type: str | None = None
    category: str | None = None
    title: str | None = None
    page: int | None = None


class AssetCollection(BaseCollectionModel[Asset]):
    pass


class VenueShow(NthpSchema):
    id: str
    name: str


class ShowDetail(NthpSchema):
    id: str
    title: str
    play: PlayShow | None = None
    playwright: PlaywrightShow | None = None
    adaptor: str | None = None
    translator: str | None = None
    company: str | None = None
    period: str | None = None
    season: str
    season_id: str | None = None
    venue: VenueShow | None = None
    date_start: FuzzyDate | None = None
    date_end: FuzzyDate | None = None
    # tour TODO
    cast: list[ShowRole]
    crew: list[ShowRole]
    cast_incomplete: bool
    cast_note: str | None = None
    crew_incomplete: bool
    crew_note: str | None = None
    assets: list[Asset]
    primary_image: str | None = None

    content: str | None = None


class ShowList(NthpSchema):
    id: str
    title: str
    playwright: PlaywrightShow | None = None
    adaptor: str | None = None
    devised: str | bool
    season: str | None = None
    season_id: str | None = None
    venue: VenueShow | None = None
    date_start: FuzzyDate | None = None
    date_end: FuzzyDate | None = None
    primary_image: str | None = None


class SeasonList(NthpSchema):
    id: str = Field(
        description="ID of the season, slugified from its canonical name",
        json_schema_extra={"example": "in-house"},
    )
    name: str = Field(
        description="Canonical name of the season",
        json_schema_extra={"example": "In House"},
    )
    aliases: list[str] = Field(
        description="Other names the season has been authored under",
        json_schema_extra={"example": ["UNCUT"]},
    )
    show_count: int = Field(
        description="Number of shows in the season",
        json_schema_extra={"example": 42},
    )


class SeasonListCollection(BaseCollectionModel[SeasonList]):
    pass


class SeasonDetail(SeasonList):
    shows: list[ShowList]


class PlaywrightShowListItem(NthpSchema):
    id: str
    title: str
    date_start: FuzzyDate | None = None
    date_end: FuzzyDate | None = None
    primary_image: str | None = None


class VenueList(NthpSchema):
    id: str
    name: str
    show_count: int
    built: int | None = None
    location: Location | None = None
    city: str | None = None


class VenueDetail(VenueList):
    assets: list[Asset] = []
    shows: list[ShowList] = []
    content: str | None = None


class VenueCollection(BaseCollectionModel[VenueList]):
    pass


class PlaywrightListItem(Playwright):
    shows: list[PlaywrightShowListItem]


class PlaywrightCollection(BaseCollectionModel[PlaywrightListItem]):
    pass


class PlayListItem(NthpSchema):
    id: str
    title: str
    playwright: Playwright
    shows: list[PlaywrightShowListItem]


class PlayCollection(BaseCollectionModel[PlayListItem]):
    pass


class YearList(NthpSchema):
    title: str = Field(
        description="Title of the academic year",
        json_schema_extra={"example": "2024-25"},
    )
    decade: int = Field(
        description="First three digits of the start year, e.g. 202 for the 2020s",
        json_schema_extra={"example": 202},
    )
    year_id: str = Field(
        description="ID of the academic year, in YYYY-YY form",
        json_schema_extra={"example": "2024-25"},
    )
    start_year: int = Field(
        description="Calendar year the academic year starts in",
        json_schema_extra={"example": 2024},
    )
    grad_year: int = Field(
        description="Calendar year students of this academic year graduate in",
        json_schema_extra={"example": 2025},
    )
    show_count: int = Field(
        description="Number of shows in the academic year",
        json_schema_extra={"example": 42},
    )


class YearListCollection(BaseCollectionModel[YearList]):
    pass


class YearDetail(YearList):
    shows: list[ShowList]
    committee: list[PersonRoleList]


class PersonShowRoleItem(NthpSchema):
    role: str | None = None
    role_type: str


class PersonShowRoles(NthpSchema):
    show_id: str
    show_title: str
    show_year_id: str
    show_year: int
    show_primary_image: str | None = None
    roles: list[PersonShowRoleItem]


class PersonCommitteeRole(NthpSchema):
    year_title: str
    year_decade: int
    year_id: str
    role: str


class PersonCommitteeRoleList(NthpSchema):
    id: str
    title: str
    headshot: str | None = None
    year_title: str
    year_decade: int
    year_id: str
    role: str


class PersonCommitteeRoleListCollection(BaseCollectionModel[PersonCommitteeRoleList]):
    pass


class PersonShowRoleList(NthpSchema):
    id: str
    title: str
    headshot: str | None = None
    role: str
    show_count: int


class PersonShowRoleListCollection(BaseCollectionModel[PersonShowRoleList]):
    pass


class Role(NthpSchema):
    role: str
    aliases: list[str]
    count: int = Field(description="Number of times the role has been held.")


class RoleCollection(BaseCollectionModel[Role]):
    pass


class RoleWithId(Role):
    id: str


class RoleWithIdCollection(BaseCollectionModel[RoleWithId]):
    pass


class PersonGraduated(NthpSchema):
    year_title: str
    year_decade: int
    year_id: str
    estimated: bool

    @classmethod
    def from_year(cls, year: int, *, estimated: bool) -> "PersonGraduated":
        return cls(
            year_title=str(year),
            year_decade=years.get_year_decade(year - 1),
            year_id=years.get_public_year_id(year - 1),
            estimated=estimated,
        )


class PersonDetail(NthpSchema):
    id: str
    title: str
    submitted: FuzzyDate | bool | None = None
    headshot: str | None = None
    graduated: PersonGraduated | None = None
    show_roles: list[PersonShowRoles]
    committee_roles: list[PersonCommitteeRole]
    content: str | None = None


class PersonIndexItem(NthpSchema):
    id: str
    title: str
    submitted: FuzzyDate | bool | None = None
    headshot: str | None = None
    graduated: PersonGraduated | None = None
    show_role_count: int
    committee_role_count: int
    has_bio: bool


class PersonIndexCollection(BaseCollectionModel[PersonIndexItem]):
    pass


class PersonCollaborator(NthpSchema):
    person_id: str
    person_name: str
    target_ids: list[str]

    model_config = RESPONSE_CONFIG  # TODO frozen=False


class PersonCollaboratorCollection(BaseCollectionModel[PersonCollaborator]):
    pass


class BaseTrivia(NthpSchema):
    quote: str = Field(
        title="Quote",
        description="The quote",
        json_schema_extra={
            "example": "Every character in this play was portrayed by a "
            "perfectly circular Victoria Sponge"
        },
    )
    submitted: FuzzyDate | None = Field(
        title="Submitted Date",
        description="The date the quote was submitted, of year, month or day "
        "precision, if null it's likely pulled from the programme or other source.",
        json_schema_extra={"example": "2022-01"},
    )


class TargetedTrivia(BaseTrivia):
    """Trivia that is targeted to a specific object (show)"""

    person_id: str | None = Field(
        title="Person ID",
        description="The person ID of the person who submitted the quote",
        json_schema_extra={"example": "fred_bloggs"},
    )
    person_name: str | None = Field(
        title="Person Name",
        description="The name of the person who submitted the quote",
        json_schema_extra={"example": "Fred Bloggs"},
    )


class TargetedTriviaCollection(BaseCollectionModel[TargetedTrivia]):
    pass


class PersonTrivia(BaseTrivia):
    """Trivia submitted by a single known person, targets want to be known"""

    target_id: str = Field(
        title="Target ID",
        description="The ID of the target of the quote",
        json_schema_extra={"example": "the_show"},
    )
    target_type: str = Field(
        title="Target Type",
        description="The type of the target of the quote",
        json_schema_extra={"example": "show"},
    )
    target_name: str = Field(
        title="Target Name",
        description="The name of the target of the quote",
        json_schema_extra={"example": "The Show"},
    )
    target_image_id: str | None = Field(
        title="Target Image ID",
        description="The image ID of the target of the quote",
        json_schema_extra={"example": "qABC123"},
    )
    # Uses YYYY, not YY_YY, 2000 means 2000-2001
    target_year: PermissiveStr | None = Field(
        title="Target Year",
        description="The year of the target of the quote",
        json_schema_extra={"example": "2000"},
    )


class PersonTriviaCollection(BaseCollectionModel[PersonTrivia]):
    pass


class HistoryRecord(NthpSchema):
    year: str = Field(
        description="Short description of the year of the record, "
        "e.g. '1940' / '1940s'",
        json_schema_extra={"example": "1940s"},
    )
    year_id: str | None = Field(
        description="Exact year ID of the record, in YYYY-YY form",
        json_schema_extra={"example": "1940-41"},
    )
    title: str = Field(
        description="Title of the record",
        json_schema_extra={"example": "Theatre built"},
    )
    description: str = Field(
        description="Description of the record, in HTML",
        json_schema_extra={"example": "<p>Theatre built in 1940</p>"},
    )


class HistoryRecordCollection(BaseCollectionModel[HistoryRecord]):
    pass


class SearchDocumentType(Enum):
    YEAR = "year"
    SHOW = "show"
    PERSON = "person"
    VENUE = "venue"


class SearchDocument(NthpSchema):
    type: SearchDocumentType
    title: str
    id: str
    image_id: str | None = None
    playwright: PlaywrightShow | None = None
    company: str | None = None
    people: list[str] | None = None
    plaintext: str | None = None


class SearchDocumentCollection(BaseCollectionModel[SearchDocument]):
    pass


class SiteStats(NthpSchema):
    build_time: datetime.datetime = Field(
        title="Build Time",
        description="When was the API built, in UTC.",
        json_schema_extra={"example": "2022-01-01T12:34:45.678901Z"},
    )
    branch: str = Field(
        description="Branch API was built from.",
        json_schema_extra={"example": "master"},
    )
    show_count: int = Field(
        title="Show Count",
        description="Number of shows in the database.",
        json_schema_extra={"example": 1234},
    )
    person_count: int = Field(
        title="Person Count",
        description="Number of people in the database.",
        json_schema_extra={"example": 1234},
    )
    person_with_bio_count: int = Field(
        title="Person with bio count",
        description="Number of people with bio records.",
        json_schema_extra={"example": 1234},
    )
    credit_count: int = Field(
        title="Credit Count",
        description="Number of credits, inc. cast/crew/committee roles.",
        json_schema_extra={"example": 1234},
    )
    trivia_count: int = Field(
        title="Trivia Count",
        description="Number of bits of trivia or stories.",
        json_schema_extra={"example": 1234},
    )
