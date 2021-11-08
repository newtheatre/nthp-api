import datetime
from typing import List, Optional, Union

import humps
from pydantic_collections import BaseCollectionModel

from nthp_build import models


class ResponseConfig:
    allow_population_by_field_name = True
    alias_generator = humps.camelize


class PersonRoleList(models.PersonRole):
    class Config(ResponseConfig):
        pass


class ShowDetail(models.Show):
    class Config(ResponseConfig):
        pass

    content: Optional[str] = None


class ShowList(models.NthpModel):
    id: str
    title: str
    playwright: Optional[str] = None
    adaptor: Optional[str] = None
    devised: Union[str, bool] = False
    season: Optional[str] = None
    date_start: Optional[datetime.date] = None
    date_end: Optional[datetime.date] = None

    class Config(ResponseConfig):
        pass


class YearList(models.NthpModel):
    class Config(ResponseConfig):
        pass

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
    fellows: List[PersonRoleList]
    commendations: List[PersonRoleList]


class PersonShowRoleItem(models.NthpModel):
    class Config(ResponseConfig):
        pass

    role: Optional[str] = None
    role_type: str


class PersonShowRoles(models.NthpModel):
    class Config(ResponseConfig):
        pass

    show_id: str
    show_title: str
    roles: List[PersonShowRoleItem]


class PersonCommitteeRole(models.NthpModel):
    class Config(ResponseConfig):
        pass

    year_title: str
    year_decade: int
    year_id: str
    role: str


class PersonCommitteeRoleList(models.NthpModel):
    class Config(ResponseConfig):
        pass

    id: str
    title: str
    headshot: Optional[str] = None
    year_title: str
    year_decade: int
    year_id: str
    role: str


class PersonCommitteeRoleListCollection(BaseCollectionModel[PersonCommitteeRoleList]):
    pass


class PersonShowRoleList(models.NthpModel):
    class Config(ResponseConfig):
        pass

    id: str
    title: str
    headshot: Optional[str] = None
    role: str
    show_count: int


class PersonShowRoleListCollection(BaseCollectionModel[PersonShowRoleList]):
    pass


class PersonDetail(models.Person):
    class Config(ResponseConfig):
        pass

    show_roles: List[PersonShowRoles]
    committee_roles: List[PersonCommitteeRole]
    content: Optional[str] = None


class SiteStats(models.NthpModel):
    class Config(ResponseConfig):
        pass

    build_time: datetime.datetime
    branch: str
    show_count: int
    person_count: int
