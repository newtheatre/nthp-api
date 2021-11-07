import datetime
from typing import List, Optional, Union

from pydantic import BaseModel


class NthpModel(BaseModel):
    pass


class Link(NthpModel):
    type: str
    href: Optional[str] = None
    snapshot: Optional[str] = None
    username: Optional[str] = None
    title: Optional[str] = None
    date: Optional[datetime.date] = None
    publisher: Optional[str] = None
    rating: Optional[str] = None
    quote: Optional[str] = None
    note: Optional[str] = None
    comment: Optional[str] = None


class Location(NthpModel):
    lat: float
    lon: float


class PersonRef(NthpModel):
    role: Optional[str] = None
    name: Optional[str] = None
    note: Optional[str] = None
    person: bool = True
    comment: Optional[str] = None


class PersonRole(NthpModel):
    person_id: Optional[str] = None
    person_name: Optional[str] = None
    role: Optional[str] = None
    note: Optional[str] = None
    is_person: bool = True
    comment: Optional[str] = None


class ShowCanonical(NthpModel):
    title: Optional[str] = None
    playwright: Optional[str] = None


class Asset(NthpModel):
    type: str
    image: Optional[str] = None
    video: Optional[str] = None
    filename: Optional[str] = None
    title: Optional[str] = None
    page: Optional[int] = None
    display_image: bool = False


class Trivia(NthpModel):
    quote: str
    name: Optional[str] = None
    submitted: Optional[datetime.date] = None


class Show(NthpModel):
    id: str
    title: str
    playwright: Optional[str] = None
    devised: Union[str, bool] = False
    improvised: bool = False
    adaptor: Optional[str] = None
    translator: Optional[str] = None
    canonical: List[ShowCanonical] = []
    student_written: bool = False
    company: Optional[str] = None
    company_sort: Optional[str] = None
    period: Optional[str] = None
    season: str
    venue: Optional[str] = None
    date_start: Optional[datetime.date] = None
    date_end: Optional[datetime.date] = None
    # tour TODO
    trivia: List[Trivia] = []
    cast: List[PersonRef] = []
    crew: List[PersonRef] = []
    cast_incomplete: bool = False
    cast_note: Optional[str] = None
    crew_incomplete: bool = False
    crew_note: Optional[str] = None
    prod_shots: Optional[str] = None
    assets: List[Asset] = []
    links: List[Link] = []
    comment: Optional[str] = None


class Committee(NthpModel):
    committee: List[PersonRef]


class Venue(NthpModel):
    title: str
    links: List[Link] = []
    built: Optional[int] = None
    images: List[str] = []
    location: Optional[Location] = None
    city: Optional[str] = None
    sort: Optional[int] = None
    comment: Optional[str] = None
