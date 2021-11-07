import datetime
from typing import List, Optional, Union

import humps
from pydantic_collections import BaseCollectionModel

from nthp_build.models import NthpModel, PersonRole, Show


class ResponseConfig:
    allow_population_by_field_name = True
    alias_generator = humps.camelize


class PersonRoleList(PersonRole):
    class Config(ResponseConfig):
        pass


class ShowDetail(Show):
    class Config(ResponseConfig):
        pass


class ShowList(NthpModel):
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


class YearList(NthpModel):
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
