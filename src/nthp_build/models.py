"""The models for ingesting data"""

import datetime
from typing import List, Optional, Union

from pydantic import BaseModel


class NthpModel(BaseModel):
    pass


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


class Trivia(NthpModel):
    quote: str
    name: Optional[str]
    submitted: Optional[datetime.date]


class Show(NthpModel):
    id: str
    title: str
    playwright: Optional[str]
    devised: Union[str, bool] = False
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
    city: Optional[str]
    sort: Optional[int]
    comment: Optional[str]


class Person(NthpModel):
    id: Optional[str]
    title: str
    submitted: Optional[datetime.date]
    headshot: Optional[str]
    # course: List[str] = [] TODO: both lists and strings
    graduated: Optional[int]
    award: Optional[str]
    # career: Optional[str] TODO: both lists and strings
    links: List[Link] = []
    news: List[Link] = []
    comment: Optional[str]
