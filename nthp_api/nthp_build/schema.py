"""The schema for outputting data"""

import datetime
from enum import Enum
from typing import Annotated, Literal

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


class Link(NthpSchema):
    """A link to a resource beyond the archive: a profile, a review, a news story."""

    type: str = Field(
        description="Type of resource, canonical name where the content repo's "
        "`_data/link-types.yaml` defines the type, otherwise as authored",
        json_schema_extra={"example": "Review"},
    )
    is_news: bool = Field(
        description="Whether the type is a news type, an article or a review",
        json_schema_extra={"example": True},
    )
    href: str | None = Field(
        default=None,
        description="URL of the resource, resolved from the username where the type "
        "templates one",
        json_schema_extra={"example": "https://twitter.com/nnt_official"},
    )
    href_snapshot: str | None = Field(
        default=None,
        description="URL of the archive.is snapshot of the resource, where one has "
        "been taken",
        json_schema_extra={"example": "https://archive.is/abc12"},
    )
    username: str | None = Field(
        default=None,
        description="Username on the service, where the type is a service",
        json_schema_extra={"example": "nnt_official"},
    )
    title: str | None = Field(
        default=None,
        description="Title of the resource, such as the headline of an article",
        json_schema_extra={"example": "Student theatre at its best"},
    )
    date: FuzzyDate | None = Field(
        default=None,
        description="Date the resource was published, of year, month or day precision",
        json_schema_extra={"example": "2022-01-31"},
    )
    publisher: str | None = Field(
        default=None,
        description="Name of the publisher, given for news and reviews",
        json_schema_extra={"example": "Impact Magazine"},
    )
    rating: str | None = Field(
        default=None,
        description="Rating a review gave, written as `x/of_y`",
        json_schema_extra={"example": "4/5"},
    )
    quote: str | None = Field(
        default=None,
        description="Short quotation summarising the resource",
        json_schema_extra={"example": "A triumph from start to finish"},
    )
    note: str | None = Field(
        default=None,
        description="Note about the resource, displayed alongside the link",
        json_schema_extra={"example": "Requires a subscription"},
    )


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
    # Intrinsic dimensions and upload date, where SmugMug knows them
    width: int | None = None
    height: int | None = None
    date: str | None = None


class AssetCollection(BaseCollectionModel[Asset]):
    pass


class VenueShow(NthpSchema):
    id: str
    name: str


class ShowTourDate(NthpSchema):
    venue: str | None = None
    date_start: FuzzyDate | None = None
    date_end: FuzzyDate | None = None
    note: str | None = None


class ShowMissingField(Enum):
    """
    A fact a show record is missing, as the old site's `_plugins/show.rb` records them.

    How many of these make a record too thin to show is left to the consumer.
    """

    DATE_START = "date_start"
    POSTER = "poster"
    EXCERPT = "excerpt"
    CAST = "cast"
    CAST_INCOMPLETE = "cast_incomplete"
    CREW = "crew"
    CREW_SHORT = "crew_short"
    PLAYWRIGHT = "playwright"
    VENUE = "venue"


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


class ShowSequenceItem(NthpSchema):
    id: str
    title: str
    primary_image: str | None = None


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
    tour: list[ShowTourDate] = []
    cast: list[ShowRole]
    crew: list[ShowRole]
    cast_incomplete: bool
    cast_note: str | None = None
    crew_incomplete: bool
    crew_note: str | None = None
    assets: list[Asset]
    primary_image: str | None = None
    missing_fields: list[ShowMissingField] = Field(
        description="Facts the show record is missing, as the old site recorded them"
    )
    ignore_missing: bool = Field(
        description="Whether the record is authored as not expected to be complete"
    )
    links: list[Link] = Field(
        default=[],
        description="Links to press reviews, news stories and recordings of the show",
    )
    ignore_missing_in_seasons: bool = Field(
        description="Whether the show is in a season whose records are not expected "
        "to be complete"
    )
    previous: ShowSequenceItem | None = Field(
        default=None, description="The show before this one across the whole archive"
    )
    next: ShowSequenceItem | None = Field(
        default=None, description="The show after this one across the whole archive"
    )
    trivia: list[TargetedTrivia] = Field(
        default=[], description="Trivia submitted about this show"
    )

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


class ShowIndexItem(NthpSchema):
    id: str
    title: str
    year_id: str = Field(
        description="ID of the academic year the show is in, in YYYY-YY form",
        json_schema_extra={"example": "2024-25"},
    )
    year: int = Field(
        description="Calendar year the academic year starts in",
        json_schema_extra={"example": 2024},
    )
    season: str = Field(description="Season as authored on the show")
    season_id: str | None = Field(
        default=None, description="ID of the season, aliases merged"
    )
    venue: VenueShow | None = None
    date_start: FuzzyDate | None = None
    date_end: FuzzyDate | None = None
    primary_image: str | None = None
    playwright_descriptor: str | None = Field(
        default=None,
        description="How the show's authorship reads, e.g. `by William Shakespeare`",
        json_schema_extra={"example": "by William Shakespeare"},
    )


class ShowIndexCollection(BaseCollectionModel[ShowIndexItem]):
    pass


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
    id: str = Field(
        description="ID of the venue, slugified from the authored venue name",
        json_schema_extra={"example": "new-theatre"},
    )
    name: str = Field(
        description="Name of the venue",
        json_schema_extra={"example": "New Theatre"},
    )
    show_count: int = Field(
        description="Number of shows at the venue",
        json_schema_extra={"example": 42},
    )
    venue_sort: str | None = Field(
        default=None,
        description="Name of the group the venue belongs to, where shows give one, "
        "for grouping venues such as Edinburgh's C venues",
        json_schema_extra={"example": "C venues"},
    )
    has_record: bool = Field(
        description="Whether the venue is documented in the archive; venues only "
        "referenced by shows are stubs, carrying no details beyond name and shows",
        json_schema_extra={"example": True},
    )
    sentinel: bool = Field(
        description="Whether the venue stands in for the absence of a venue, such as "
        "an unknown venue or an online performance",
        json_schema_extra={"example": False},
    )
    built: int | None = Field(
        default=None,
        description="Year the venue was built",
        json_schema_extra={"example": 1965},
    )
    location: Location | None = None
    city: str | None = Field(
        default=None,
        description="City the venue is in",
        json_schema_extra={"example": "Nottingham"},
    )


class VenueDetail(VenueList):
    assets: list[Asset] = []
    links: list[Link] = Field(
        default=[], description="Links to the venue's own site and other resources"
    )
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


class PersonAwardHolder(NthpSchema):
    id: str = Field(
        description="ID of the person", json_schema_extra={"example": "fred_bloggs"}
    )
    title: str = Field(
        description="Name of the person", json_schema_extra={"example": "Fred Bloggs"}
    )
    headshot: str | None = Field(
        default=None,
        description="Image ID of the person's headshot",
        json_schema_extra={"example": "qABC123"},
    )


class YearDetail(YearList):
    shows: list[ShowList]
    committee: list[PersonRoleList]
    fellows: list[PersonAwardHolder] = Field(
        default=[],
        description="People awarded a Fellowship, by the year they graduated in",
    )
    commendations: list[PersonAwardHolder] = Field(
        default=[],
        description="People awarded a Commendation, by the year they graduated in",
    )


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
    headshot: Asset | None = None
    graduated: PersonGraduated | None = None
    show_roles: list[PersonShowRoles]
    committee_roles: list[PersonCommitteeRole]
    course: list[str] = Field(
        default=[],
        description="Courses the person studied",
        json_schema_extra={"example": ["English"]},
    )
    award: str | None = Field(
        default=None,
        description="Award the person received on leaving the theatre, as authored; "
        "usually Fellowship, Commendation, Merit or Union Prize, but not held to "
        "that set",
        json_schema_extra={"example": "Fellowship"},
    )
    careers: list[str] = Field(
        default=[],
        description="Careers the person has followed, theatre related or not, as "
        "authored; the content repo's `_data/careers.yaml` lists the recognised "
        "theatre careers but records are not held to it",
        json_schema_extra={"example": ["Director"]},
    )
    student: bool = Field(
        description="Whether the person is likely still a student, worked out from "
        "their graduation year and the date the API was built, so it goes stale "
        "between builds",
        json_schema_extra={"example": False},
    )
    links: list[Link] = Field(
        default=[], description="Links to the person's profiles beyond the archive"
    )
    news: list[Link] = Field(
        default=[], description="Links to news stories about the person"
    )
    trivia: list[PersonTrivia] = Field(
        default=[], description="Trivia submitted by this person"
    )
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


class HistoryRecordImage(NthpSchema):
    href: str = Field(
        description="URL of the image",
        json_schema_extra={"example": "https://photos.newtheatre.org.uk/i-abc123.jpg"},
    )
    alt: str = Field(
        description="Short caption describing the image",
        json_schema_extra={"example": "The old auditorium"},
    )


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
    image: HistoryRecordImage | None = Field(
        default=None, description="Image illustrating the record, where there is one"
    )


class HistoryRecordCollection(BaseCollectionModel[HistoryRecord]):
    pass


class SearchDocumentType(Enum):
    YEAR = "year"
    SHOW = "show"
    PERSON = "person"
    VENUE = "venue"


class SearchDocumentBase(NthpSchema):
    """
    Fields every search document carries, whatever it describes.

    Documents are faceted per type: the consumer builds its own index from them,
    so each carries the fields worth searching or filtering on and nothing more.
    Anything absent is omitted rather than sent as null, keeping the corpus small.
    """

    type: SearchDocumentType = Field(
        description="What the document describes, the union's discriminator"
    )
    title: str = Field(
        description="Name of the record, the primary field to search on",
        json_schema_extra={"example": "Macbeth"},
    )
    id: str = Field(
        description="ID of the record, as its own document is keyed by",
        json_schema_extra={"example": "2024-25/macbeth"},
    )
    image_id: str | None = Field(
        default=None,
        description="Image illustrating the record, where there is one",
        json_schema_extra={"example": "abc12"},
    )


class SearchDocumentShow(SearchDocumentBase):
    """A show, the archive's principal record."""

    type: Literal[SearchDocumentType.SHOW]
    year_id: str = Field(
        description="ID of the academic year the show ran in, in YYYY-YY form",
        json_schema_extra={"example": "2024-25"},
    )
    year: int = Field(
        description="Calendar year the academic year starts in",
        json_schema_extra={"example": 2024},
    )
    decade: int = Field(
        description="First three digits of the start year, e.g. 202 for the 2020s",
        json_schema_extra={"example": 202},
    )
    season: str = Field(
        description="Season as authored on the show",
        json_schema_extra={"example": "Autumn Season"},
    )
    season_id: str | None = Field(
        default=None,
        description="ID of the season, where the authored season is a known one",
        json_schema_extra={"example": "autumn_season"},
    )
    venue_id: str | None = Field(
        default=None,
        description="ID of the venue the show ran at",
        json_schema_extra={"example": "nottingham-new-theatre"},
    )
    venue_name: str | None = Field(
        default=None,
        description="Name of the venue as authored on the show",
        json_schema_extra={"example": "Nottingham New Theatre"},
    )
    date_start: FuzzyDate | None = Field(
        default=None,
        description="Date the show opened, of year, month or day precision",
        json_schema_extra={"example": "2024-11-13"},
    )
    playwright: str | None = Field(
        default=None,
        description="How the show describes its authorship, e.g. `by Shakespeare`, "
        "`Devised` or `Various Writers`",
        json_schema_extra={"example": "by William Shakespeare"},
    )
    company: str | None = Field(
        default=None,
        description="Company that staged the show, where it was not the theatre",
        json_schema_extra={"example": "Nottingham New Theatre"},
    )
    people: list[str] | None = Field(
        default=None,
        description="Names of everyone credited on the show, cast and crew alike",
        json_schema_extra={"example": ["Fred Bloggs"]},
    )
    plaintext: str | None = Field(
        default=None,
        description="The show's description, markup stripped",
        json_schema_extra={"example": "A tragedy of ambition."},
    )


class SearchDocumentPerson(SearchDocumentBase):
    """Anyone credited on a show or committee, whether or not they have a bio."""

    type: Literal[SearchDocumentType.PERSON]
    has_bio: bool = Field(
        description="Whether the archive holds a document about the person, as "
        "opposed to knowing them only from the credits they appear in",
        json_schema_extra={"example": True},
    )
    graduation_year: str | None = Field(
        default=None,
        description="ID of the academic year the person graduated in, in YYYY-YY "
        "form; absent where they are yet to graduate or nothing is known",
        json_schema_extra={"example": "2024-25"},
    )
    graduation_decade: int | None = Field(
        default=None,
        description="First three digits of the graduation year's start year",
        json_schema_extra={"example": 202},
    )
    graduation_estimated: bool | None = Field(
        default=None,
        description="Whether the graduation year is estimated from the person's "
        "credits rather than authored",
        json_schema_extra={"example": False},
    )
    course: list[str] | None = Field(
        default=None,
        description="Courses the person studied",
        json_schema_extra={"example": ["English"]},
    )
    careers: list[str] | None = Field(
        default=None,
        description="Careers the person has followed, theatre related or not",
        json_schema_extra={"example": ["Director"]},
    )
    award: str | None = Field(
        default=None,
        description="Award the person received on leaving the theatre, as authored",
        json_schema_extra={"example": "Fellowship"},
    )
    show_roles: list[str] | None = Field(
        default=None,
        description="Distinct roles the person has taken on a show, crew roles under "
        "their canonical name and acting as `Actor`",
        json_schema_extra={"example": ["Actor", "Director"]},
    )
    committee_roles: list[str] | None = Field(
        default=None,
        description="Distinct committee positions the person has held, under their "
        "canonical name",
        json_schema_extra={"example": ["Publicity Manager"]},
    )
    show_count: int = Field(
        description="Number of shows the person is credited on",
        json_schema_extra={"example": 7},
    )
    year_ids: list[str] | None = Field(
        default=None,
        description="IDs of the academic years the person is credited in, whether "
        "on a show or a committee",
        json_schema_extra={"example": ["2023-24", "2024-25"]},
    )
    plaintext: str | None = Field(
        default=None,
        description="The person's biography, markup stripped",
        json_schema_extra={"example": "Fred read English and directed a lot."},
    )


class SearchDocumentVenue(SearchDocumentBase):
    """A venue, whether or not the archive holds a document about it."""

    type: Literal[SearchDocumentType.VENUE]
    city: str | None = Field(
        default=None,
        description="City the venue is in, where the archive holds a document for it",
        json_schema_extra={"example": "Nottingham"},
    )
    show_count: int = Field(
        description="Number of shows that ran at the venue",
        json_schema_extra={"example": 42},
    )
    plaintext: str | None = Field(
        default=None,
        description="The venue's description, markup stripped",
        json_schema_extra={"example": "A studio theatre on University Park."},
    )


class SearchDocumentYear(SearchDocumentBase):
    """An academic year."""

    type: Literal[SearchDocumentType.YEAR]
    decade: int = Field(
        description="First three digits of the start year, e.g. 202 for the 2020s",
        json_schema_extra={"example": 202},
    )
    show_count: int = Field(
        description="Number of shows in the academic year",
        json_schema_extra={"example": 42},
    )


SearchDocument = Annotated[
    SearchDocumentShow
    | SearchDocumentPerson
    | SearchDocumentVenue
    | SearchDocumentYear,
    Field(discriminator="type"),
]


class SearchDocumentCollection(BaseCollectionModel[SearchDocument]):
    pass


class SearchDocumentShowCollection(BaseCollectionModel[SearchDocumentShow]):
    pass


class SearchDocumentPersonCollection(BaseCollectionModel[SearchDocumentPerson]):
    pass


class SearchDocumentVenueCollection(BaseCollectionModel[SearchDocumentVenue]):
    pass


class SearchDocumentYearCollection(BaseCollectionModel[SearchDocumentYear]):
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
    search_document_count: int = Field(
        title="Search Document Count",
        description="Number of documents in the search corpus, shows, people, venues "
        "and years together.",
        json_schema_extra={"example": 1234},
    )
