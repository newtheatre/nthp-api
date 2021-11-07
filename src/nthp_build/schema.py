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


class PersonDetail(models.Person):
    class Config(ResponseConfig):
        pass

    show_roles: List[PersonShowRoles] = []
    content: Optional[str] = None
