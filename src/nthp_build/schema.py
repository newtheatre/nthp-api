"""The schema for outputting data"""

import datetime
from enum import Enum
from typing import FrozenSet, List, Optional, Union

import humps
from pydantic import BaseModel, Field
from pydantic_collections import BaseCollectionModel

from nthp_build import models, years


class ResponseConfig:
    allow_population_by_field_name = True
    alias_generator = humps.camelize
    frozen = True


class NthpSchema(BaseModel):
    class Config(ResponseConfig):
        pass


class PersonRoleList(models.PersonRole):
    class Config(ResponseConfig):
        pass


class PersonList(NthpSchema):
    id: str
    name: str
    is_person: bool
    headshot: Optional[str]
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
    id: Optional[str]
    name: Optional[str]
    person_id: Optional[str]


class PlaywrightShow(Playwright):
    type: PlaywrightType
    descriptor: Optional[str]
    student_written: bool


class ShowRole(NthpSchema):
    role: Optional[str]
    person: Optional[PersonList]
    note: Optional[str]


class Asset(NthpSchema):
    type: str
    source: str
    id: str
    mime_type: Optional[str]
    category: Optional[str]
    title: Optional[str]
    page: Optional[int]


class AssetCollection(BaseCollectionModel[Asset]):
    pass


class ShowDetail(NthpSchema):
    id: str
    title: str
    play: Optional[PlayShow]
    playwright: Optional[PlaywrightShow]
    adaptor: Optional[str]
    translator: Optional[str]
    # canonical: List[ShowCanonical] = []
    company: Optional[str]
    # company_sort: Optional[str]
    period: Optional[str]
    season: str
    # season_sort: Optional[int]
    # venue: Optional[str]
    date_start: Optional[datetime.date]
    date_end: Optional[datetime.date]
    # tour TODO
    cast: List[ShowRole]
    crew: List[ShowRole]
    cast_incomplete: bool
    cast_note: Optional[str]
    crew_incomplete: bool
    crew_note: Optional[str]
    assets: List[Asset]
    primary_image: Optional[str]
    # links: List[Link] = []

    content: Optional[str]


class ShowList(NthpSchema):
    id: str
    title: str
    playwright: Optional[PlaywrightShow]
    adaptor: Optional[str]
    devised: Union[str, bool]
    season: Optional[str]
    date_start: Optional[datetime.date]
    date_end: Optional[datetime.date]
    primary_image: Optional[str]


class PlaywrightShowListItem(NthpSchema):
    id: str
    title: str
    date_start: Optional[datetime.date]
    date_end: Optional[datetime.date]
    primary_image: Optional[str]


class PlaywrightListItem(Playwright):
    shows: List[PlaywrightShowListItem]


class PlaywrightCollection(BaseCollectionModel[PlaywrightListItem]):
    pass


class PlayListItem(NthpSchema):
    id: str
    title: str
    playwright: Playwright
    shows: List[PlaywrightShowListItem]


class PlayCollection(BaseCollectionModel[PlayListItem]):
    pass


class YearList(NthpSchema):
    title: str
    decade: int
    year_id: str
    start_year: int
    grad_year: int
    show_count: int


class YearListCollection(BaseCollectionModel[YearList]):
    pass


class YearDetail(YearList):
    shows: List[ShowList]
    committee: List[PersonRoleList]
    # fellows: List[PersonRoleList]
    # commendations: List[PersonRoleList]


class PersonShowRoleItem(NthpSchema):
    role: Optional[str]
    role_type: str


class PersonShowRoles(NthpSchema):
    show_id: str
    show_title: str
    roles: List[PersonShowRoleItem]


class PersonCommitteeRole(NthpSchema):
    year_title: str
    year_decade: int
    year_id: str
    role: str


class PersonCommitteeRoleList(NthpSchema):
    id: str
    title: str
    headshot: Optional[str]
    year_title: str
    year_decade: int
    year_id: str
    role: str


class PersonCommitteeRoleListCollection(BaseCollectionModel[PersonCommitteeRoleList]):
    pass


class PersonShowRoleList(NthpSchema):
    id: str
    title: str
    headshot: Optional[str]
    role: str
    show_count: int


class PersonShowRoleListCollection(BaseCollectionModel[PersonShowRoleList]):
    pass


class Role(NthpSchema):
    role: str
    aliases: List[str]


class RoleCollection(BaseCollectionModel[Role]):
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
            year_id=years.get_year_id(year - 1),
            estimated=estimated,
        )


class PersonDetail(NthpSchema):
    id: str
    title: str
    submitted: Optional[datetime.date]
    headshot: Optional[str]
    graduated: Optional[PersonGraduated]
    show_roles: List[PersonShowRoles]
    committee_roles: List[PersonCommitteeRole]
    content: Optional[str]


class PersonCollaborator(NthpSchema):
    person_id: str
    person_name: str
    target_ids: List[str]

    class Config(ResponseConfig):
        frozen = False  # Cannot be frozen as we need an ordered list


class PersonCollaboratorCollection(BaseCollectionModel[PersonCollaborator]):
    pass


class BaseTrivia(NthpSchema):
    quote: str = Field(
        title="Quote",
        description="The quote",
        example="Every character in this play was portrayed by a perfectly circular "
        "Victoria Sponge",
    )
    submitted: Optional[datetime.date] = Field(
        title="Submitted Date",
        description="The date the quote was submitted, if null it's likely pulled from "
        "the programme or other source.",
        example="2022-01-01",
    )


class TargetedTrivia(BaseTrivia):
    """Trivia that is targeted to a specific object (show)"""

    person_id: Optional[str] = Field(
        title="Person ID",
        description="The person ID of the person who submitted the quote",
        example="fred_bloggs",
    )
    person_name: Optional[str] = Field(
        title="Person Name",
        description="The name of the person who submitted the quote",
        example="Fred Bloggs",
    )


class TargetedTriviaCollection(BaseCollectionModel[TargetedTrivia]):
    pass


class PersonTrivia(BaseTrivia):
    """Trivia submitted by a single known person, targets want to be known"""

    target_id: str = Field(
        title="Target ID",
        description="The ID of the target of the quote",
        example="the_show",
    )
    target_type: str = Field(
        title="Target Type",
        description="The type of the target of the quote",
        example="show",
    )
    target_name: str = Field(
        title="Target Name",
        description="The name of the target of the quote",
        example="The Show",
    )
    target_image_id: Optional[str] = Field(
        title="Target Image ID",
        description="The image ID of the target of the quote",
        example="qABC123",
    )
    # Uses YYYY, not YY_YY, 2000 means 2000-2001
    target_year: Optional[str] = Field(
        title="Target Year",
        description="The year of the target of the quote",
        example="2000",
    )


class PersonTriviaCollection(BaseCollectionModel[PersonTrivia]):
    pass


class HistoryRecord(NthpSchema):
    year: str = Field(
        description="Short description of the year of the record, "
        "e.g. '1940' / '1940s'",
        example="1940s",
    )
    year_id: Optional[str] = Field(
        description="Exact year ID of the record", example="40_41"
    )
    title: str = Field(description="Title of the record", example="Theatre built")
    description: str = Field(
        description="Description of the record, in HTML",
        example="<p>Theatre built in 1940</p>",
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
    image_id: Optional[str]
    playwright: Optional[PlaywrightShow]
    company: Optional[str]
    people: Optional[List[str]]
    plaintext: Optional[str]


class SearchDocumentCollection(BaseCollectionModel[SearchDocument]):
    pass


class SiteStats(NthpSchema):
    build_time: datetime.datetime = Field(
        title="Build Time",
        description="When was the API built.",
        example="2022-01-01T12:34:45.678901",
    )
    branch: str = Field(description="Branch API was built from.", example="master")
    show_count: int = Field(
        title="Show Count", description="Number of shows in the database.", example=1234
    )
    person_count: int = Field(
        title="Person Count",
        description="Number of people in the database.",
        example=1234,
    )
    person_with_bio_count: int = Field(
        title="Person with bio count",
        description="Number of people with bio records.",
        example=1234,
    )
    credit_count: int = Field(
        title="Credit Count",
        description="Number of credits, inc. cast/crew/committee roles.",
        example=1234,
    )
    trivia_count: int = Field(
        title="Trivia Count",
        description="Number of bits of trivia or stories.",
        example=1234,
    )
