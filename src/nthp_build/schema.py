"""The schema for outputting data"""

import datetime
from enum import Enum
from typing import FrozenSet, List, Optional, Union

import humps
from pydantic import BaseModel
from pydantic_collections import BaseCollectionModel

from nthp_build import models


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
    image: Optional[str]
    video: Optional[str]
    filename: Optional[str]
    title: Optional[str]
    page: Optional[int]
    display_image: bool


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
    # trivia: List[Trivia] = []
    cast: List[ShowRole]
    crew: List[ShowRole]
    cast_incomplete: bool
    cast_note: Optional[str]
    crew_incomplete: bool
    crew_note: Optional[str]
    prod_shots: Optional[str]
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


class PersonDetail(models.Person):
    class Config(ResponseConfig):
        pass

    show_roles: List[PersonShowRoles]
    committee_roles: List[PersonCommitteeRole]
    content: Optional[str]


class PersonCollaborator(NthpSchema):
    person_id: str
    person_name: str
    target_ids: FrozenSet[str]


class PersonCollaboratorCollection(BaseCollectionModel[PersonCollaborator]):
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
    playwright: Optional[PlaywrightShow]
    company: Optional[str]
    people: Optional[List[str]]
    plaintext: Optional[str]


class SearchDocumentCollection(BaseCollectionModel[SearchDocument]):
    pass


class SiteStats(NthpSchema):
    build_time: datetime.datetime
    branch: str
    show_count: int
    person_count: int
