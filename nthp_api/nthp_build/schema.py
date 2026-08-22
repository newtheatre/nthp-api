"""
The schema for outputting data.

Shapes follow the rules in `docs/25-Response shape consistency.md`: a record's own
id is `id`, references are one shared ref model per entity type, display strings are
`title` or `name` but never both, images are an `ImageRef` in lists and a full
`Asset` in detail, counts are `{singularNoun}Count`, enum values are lowercase, and
every nullable field carries a default so the spec's `required` is honest.
"""

import datetime
from enum import Enum
from typing import Annotated, Literal

import humps
from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import ComputedFieldInfo, FieldInfo
from pydantic_collections import BaseCollectionModel

from nthp_api.nthp_build import models, years
from nthp_api.nthp_build.fields import FuzzyDate


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


class ImageRef(NthpSchema):
    """
    An image referenced from a list or a summary, by key and intrinsic size.

    Detail documents carry the full `Asset` instead. Dimensions are absent only
    where SmugMug could not answer for the key.
    """

    id: str = Field(
        description="SmugMug image key",
        json_schema_extra={"example": "qABC123"},
    )
    width: int | None = Field(
        default=None,
        description="Intrinsic width of the image in pixels",
        json_schema_extra={"example": 1600},
    )
    height: int | None = Field(
        default=None,
        description="Intrinsic height of the image in pixels",
        json_schema_extra={"example": 1200},
    )


class Asset(ImageRef):
    """A file the archive holds about a record: an image, a video or a document."""

    type: str = Field(
        description="Kind of asset, one of `album`, `image`, `video` or `other`",
        json_schema_extra={"example": "image"},
    )
    source: str = Field(
        description="Where the asset is held, `smugmug` or `file`",
        json_schema_extra={"example": "smugmug"},
    )
    mime_type: str | None = Field(
        default=None,
        description="Mime type of the asset, where one applies",
        json_schema_extra={"example": "image/jpeg"},
    )
    category: str | None = Field(
        default=None,
        description="What the asset depicts, as authored; poster, flyer, programme "
        "and headshot are the recognised categories",
        json_schema_extra={"example": "poster"},
    )
    title: str | None = Field(
        default=None,
        description="Title of the asset, as authored",
        json_schema_extra={"example": "Programme"},
    )
    page: int | None = Field(
        default=None,
        description="Page of the document the asset is, where it is one of several",
        json_schema_extra={"example": 2},
    )
    uploaded_at: datetime.datetime | None = Field(
        default=None,
        description="When the asset was uploaded to SmugMug, where SmugMug knows",
        json_schema_extra={"example": "2022-01-01T12:34:45.678901Z"},
    )


class AssetCollection(BaseCollectionModel[Asset]):
    pass


class PersonRef(NthpSchema):
    """A person credited somewhere, whether or not the archive holds a bio."""

    id: str = Field(
        description="ID of the person",
        json_schema_extra={"example": "fred_bloggs"},
    )
    title: str = Field(
        description="Name of the person",
        json_schema_extra={"example": "Fred Bloggs"},
    )
    is_person: bool = Field(
        description="Whether the credit names a person rather than a group",
        json_schema_extra={"example": True},
    )
    has_bio: bool = Field(
        description="Whether the archive holds a document about the person, as "
        "opposed to knowing them only from the credits they appear in",
        json_schema_extra={"example": True},
    )
    headshot: ImageRef | None = Field(
        default=None, description="The person's headshot, where there is one"
    )


class VenueRef(NthpSchema):
    """A venue a show ran at."""

    id: str = Field(
        description="ID of the venue, slugified from the authored venue name",
        json_schema_extra={"example": "new-theatre"},
    )
    name: str = Field(
        description="Name of the venue as authored on the show",
        json_schema_extra={"example": "New Theatre"},
    )


class YearRef(NthpSchema):
    """An academic year, as every year reference gives it."""

    id: str = Field(
        description="ID of the academic year, in YYYY-YY form",
        json_schema_extra={"example": "2024-25"},
    )
    title: str = Field(
        description="Title of the academic year",
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
    decade: int = Field(
        description="Calendar year the start year's decade begins in",
        json_schema_extra={"example": 2020},
    )

    @classmethod
    def from_start_year(cls, start_year: int) -> "YearRef":
        return cls(
            id=years.get_public_year_id(start_year),
            title=years.get_year_title(start_year),
            start_year=start_year,
            grad_year=start_year + 1,
            decade=years.get_year_decade(start_year),
        )


class ShowRef(NthpSchema):
    """A show referenced from another record."""

    id: str = Field(
        description="ID of the show, `{yearId}/{slug}`",
        json_schema_extra={"example": "2024-25/macbeth"},
    )
    title: str = Field(
        description="Title of the show", json_schema_extra={"example": "Macbeth"}
    )
    year_id: str = Field(
        description="ID of the academic year the show is in, in YYYY-YY form",
        json_schema_extra={"example": "2024-25"},
    )
    year: int = Field(
        description="Calendar year the academic year starts in",
        json_schema_extra={"example": 2024},
    )
    primary_image: ImageRef | None = Field(
        default=None, description="Image standing for the show, where there is one"
    )


class ShowDatedRef(ShowRef):
    """A show reference carrying its run, for lists ordered by date."""

    date_start: FuzzyDate | None = Field(
        default=None,
        description="Date the show opened, of year, month or day precision",
        json_schema_extra={"example": "2024-11-13"},
    )
    date_end: FuzzyDate | None = Field(
        default=None,
        description="Date the show closed, of year, month or day precision",
        json_schema_extra={"example": "2024-11-16"},
    )


class PlayRef(NthpSchema):
    """A play, the work a show staged."""

    id: str = Field(
        description="ID of the play, slugified from its title",
        json_schema_extra={"example": "macbeth"},
    )
    title: str = Field(
        description="Title of the play", json_schema_extra={"example": "Macbeth"}
    )


class PlaywrightRef(NthpSchema):
    """
    Whoever wrote the work a show staged.

    Every field is absent for a show that was devised, improvised, of unknown
    authorship or written by several hands.
    """

    id: str | None = Field(
        default=None,
        description="ID of the playwright, slugified from their name",
        json_schema_extra={"example": "william_shakespeare"},
    )
    name: str | None = Field(
        default=None,
        description="Name of the playwright",
        json_schema_extra={"example": "William Shakespeare"},
    )
    person_id: str | None = Field(
        default=None,
        description="ID of the person the playwright is, where a student wrote it",
        json_schema_extra={"example": "fred_bloggs"},
    )


class PlaywrightType(Enum):
    PLAYWRIGHT = "playwright"
    VARIOUS = "various"
    UNKNOWN = "unknown"
    DEVISED = "devised"
    IMPROVISED = "improvised"


class PlaywrightShow(PlaywrightRef):
    """How a show came to be written, as shown alongside its title."""

    type: PlaywrightType = Field(description="How the show was written")
    descriptor: str | None = Field(
        default=None,
        description="How the show's authorship reads",
        json_schema_extra={"example": "by William Shakespeare"},
    )
    student_written: bool = Field(
        description="Whether a student of the university wrote it",
        json_schema_extra={"example": False},
    )


class PersonCredit(NthpSchema):
    """A person credited in a role, on a show or on a committee."""

    role: str | None = Field(
        default=None,
        description="Role as authored",
        json_schema_extra={"example": "Director"},
    )
    person: PersonRef | None = Field(
        default=None, description="The person credited, where the credit names one"
    )
    note: str | None = Field(
        default=None,
        description="Note about the credit, displayed alongside it",
        json_schema_extra={"example": "Act 2 only"},
    )


class ShowTourDate(NthpSchema):
    venue: str | None = Field(
        default=None,
        description="Venue the show toured to, as authored",
        json_schema_extra={"example": "Lakeside Arts"},
    )
    date_start: FuzzyDate | None = Field(
        default=None, description="Date the run at the venue opened"
    )
    date_end: FuzzyDate | None = Field(
        default=None, description="Date the run at the venue closed"
    )
    note: str | None = Field(default=None, description="Note about the tour date")


class ShowMissingField(Enum):
    """
    A fact a show record is missing, as the old site's `_plugins/show.rb` records them.

    Values spell the camelCase field the fact is missing from. How many of these make
    a record too thin to show is left to the consumer.
    """

    DATE_START = "dateStart"
    POSTER = "poster"
    EXCERPT = "excerpt"
    CAST = "cast"
    CAST_INCOMPLETE = "castIncomplete"
    CREW = "crew"
    CREW_SHORT = "crewShort"
    PLAYWRIGHT = "playwright"
    VENUE = "venue"


class TriviaTargetType(Enum):
    SHOW = "show"


class TriviaTarget(ShowRef):
    """What a piece of trivia is about; only shows carry trivia today."""

    type: TriviaTargetType = Field(description="What kind of record the target is")


class Trivia(NthpSchema):
    """A story or quote submitted about a show."""

    quote: str = Field(
        description="The quote",
        json_schema_extra={
            "example": "Every character in this play was portrayed by a "
            "perfectly circular Victoria Sponge"
        },
    )
    submitted_date: FuzzyDate | None = Field(
        default=None,
        description="The date the quote was submitted, of year, month or day "
        "precision; absent where it is likely pulled from the programme or another "
        "source",
        json_schema_extra={"example": "2022-01"},
    )
    person: PersonRef | None = Field(
        default=None,
        description="Who submitted the quote, where they are known; absent on a "
        "person's own document, where the person is the one submitting",
    )
    target: TriviaTarget | None = Field(
        default=None,
        description="What the quote is about; absent on the target's own document",
    )


class ShowIndexItem(NthpSchema):
    """A show as the index of every show gives it, kept light for browse pages."""

    id: str = Field(
        description="ID of the show, `{yearId}/{slug}`",
        json_schema_extra={"example": "2024-25/macbeth"},
    )
    title: str = Field(
        description="Title of the show", json_schema_extra={"example": "Macbeth"}
    )
    year_id: str = Field(
        description="ID of the academic year the show is in, in YYYY-YY form",
        json_schema_extra={"example": "2024-25"},
    )
    year: int = Field(
        description="Calendar year the academic year starts in",
        json_schema_extra={"example": 2024},
    )
    season: str = Field(
        description="Season as authored on the show",
        json_schema_extra={"example": "In House"},
    )
    season_id: str | None = Field(
        default=None,
        description="ID of the season, aliases merged",
        json_schema_extra={"example": "in-house"},
    )
    venue: VenueRef | None = Field(
        default=None, description="Venue the show ran at, where one is authored"
    )
    date_start: FuzzyDate | None = Field(
        default=None,
        description="Date the show opened, of year, month or day precision",
        json_schema_extra={"example": "2024-11-13"},
    )
    date_end: FuzzyDate | None = Field(
        default=None,
        description="Date the show closed, of year, month or day precision",
        json_schema_extra={"example": "2024-11-16"},
    )
    primary_image: ImageRef | None = Field(
        default=None, description="Image standing for the show, where there is one"
    )
    playwright_descriptor: str | None = Field(
        default=None,
        description="How the show's authorship reads",
        json_schema_extra={"example": "by William Shakespeare"},
    )


class ShowIndexCollection(BaseCollectionModel[ShowIndexItem]):
    pass


class ShowList(ShowIndexItem):
    """A show as the lists embedded in year, season and venue documents give it."""

    playwright: PlaywrightShow | None = Field(
        default=None, description="How the show came to be written"
    )
    adaptor: str | None = Field(
        default=None,
        description="Who adapted the work, as authored",
        json_schema_extra={"example": "Fred Bloggs"},
    )
    devised: bool = Field(
        description="Whether the show was devised rather than written",
        json_schema_extra={"example": False},
    )


class ShowDetail(ShowList):
    """Everything the archive holds about a show."""

    play: PlayRef | None = Field(
        default=None, description="The play staged, where the show staged one"
    )
    translator: str | None = Field(
        default=None,
        description="Who translated the work, as authored",
        json_schema_extra={"example": "Fred Bloggs"},
    )
    company: str | None = Field(
        default=None,
        description="Company that staged the show, where it was not the theatre",
        json_schema_extra={"example": "Nottingham New Theatre"},
    )
    period: str | None = Field(
        default=None,
        description="Period the show is set in, as authored",
        json_schema_extra={"example": "Victorian"},
    )
    tour: list[ShowTourDate] = Field(
        default=[], description="Dates the show toured to other venues"
    )
    cast: list[PersonCredit] = Field(default=[], description="Who appeared in the show")
    crew: list[PersonCredit] = Field(default=[], description="Who made the show")
    cast_incomplete: bool = Field(
        description="Whether the cast list is known to be incomplete"
    )
    cast_note: str | None = Field(
        default=None, description="Note about the cast, displayed alongside it"
    )
    crew_incomplete: bool = Field(
        description="Whether the crew list is known to be incomplete"
    )
    crew_note: str | None = Field(
        default=None, description="Note about the crew, displayed alongside it"
    )
    assets: list[Asset] = Field(
        default=[], description="Images, videos and documents held about the show"
    )
    missing_fields: list[ShowMissingField] = Field(
        default=[],
        description="Facts the show record is missing, as the old site recorded them",
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
    previous: ShowRef | None = Field(
        default=None, description="The show before this one across the whole archive"
    )
    next: ShowRef | None = Field(
        default=None, description="The show after this one across the whole archive"
    )
    trivia: list[Trivia] = Field(
        default=[], description="Trivia submitted about this show"
    )
    content: str | None = Field(
        default=None, description="The show's description, in HTML"
    )


class OnThisDayShow(ShowRef):
    """A show that was running on a given day of the year."""

    date_start: FuzzyDate = Field(
        description="First day of the run, always to day precision"
    )
    date_end: FuzzyDate | None = Field(
        default=None, description="Last day of the run, where the run spans more days"
    )


class OnThisDayShowCollection(BaseCollectionModel[OnThisDayShow]):
    pass


class PosterItem(ShowRef):
    """A show's primary image, for picking posters to display."""

    primary_image: ImageRef = Field(description="The show's primary image")


class PosterCollection(BaseCollectionModel[PosterItem]):
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
        default=[],
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
    shows: list[ShowList] = Field(default=[], description="Shows in the season")


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
    group: str | None = Field(
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
    location: Location | None = Field(
        default=None, description="Where the venue is, where it is known"
    )
    city: str | None = Field(
        default=None,
        description="City the venue is in",
        json_schema_extra={"example": "Nottingham"},
    )


class VenueDetail(VenueList):
    assets: list[Asset] = Field(default=[], description="Images held of the venue")
    links: list[Link] = Field(
        default=[], description="Links to the venue's own site and other resources"
    )
    shows: list[ShowList] = Field(default=[], description="Shows that ran at the venue")
    content: str | None = Field(
        default=None, description="The venue's description, in HTML"
    )


class VenueCollection(BaseCollectionModel[VenueList]):
    pass


class PlaywrightListItem(PlaywrightRef):
    shows: list[ShowDatedRef] = Field(
        default=[], description="Shows of the playwright's work"
    )


class PlaywrightCollection(BaseCollectionModel[PlaywrightListItem]):
    pass


class PlayListItem(PlayRef):
    playwright: PlaywrightRef = Field(description="Who wrote the play")
    shows: list[ShowDatedRef] = Field(default=[], description="Shows of the play")


class PlayCollection(BaseCollectionModel[PlayListItem]):
    pass


class YearList(YearRef):
    show_count: int = Field(
        description="Number of shows in the academic year",
        json_schema_extra={"example": 42},
    )


class YearListCollection(BaseCollectionModel[YearList]):
    pass


class YearDetail(YearList):
    shows: list[ShowList] = Field(default=[], description="Shows in the academic year")
    committee: list[PersonCredit] = Field(
        default=[], description="Who sat on the committee in the academic year"
    )
    fellows: list[PersonRef] = Field(
        default=[],
        description="People awarded a Fellowship, by the year they graduated in",
    )
    commendations: list[PersonRef] = Field(
        default=[],
        description="People awarded a Commendation, by the year they graduated in",
    )


class ShowRoleType(Enum):
    CAST = "cast"
    CREW = "crew"


class PersonShowRoleItem(NthpSchema):
    role: str | None = Field(
        default=None,
        description="Role as authored, absent for a cast credit naming no part",
        json_schema_extra={"example": "Director"},
    )
    role_type: ShowRoleType = Field(description="Whether the role is cast or crew")


class PersonShowRoles(NthpSchema):
    """What a person did on one show."""

    show: ShowRef = Field(description="The show the person worked on")
    roles: list[PersonShowRoleItem] = Field(
        default=[], description="Roles the person took on the show"
    )


class PersonCommitteeRole(NthpSchema):
    """A committee position a person held for one academic year."""

    year: YearRef = Field(description="The academic year the position was held in")
    role: str = Field(
        description="Position as authored",
        json_schema_extra={"example": "Publicity Manager"},
    )


class PersonCommitteeRoleList(NthpSchema):
    """A person who held a committee position, as the role's own index gives them."""

    person: PersonRef = Field(description="The person who held the position")
    year: YearRef = Field(description="The academic year the position was held in")
    role: str = Field(
        description="Position as authored",
        json_schema_extra={"example": "Publicity Manager"},
    )


class PersonCommitteeRoleListCollection(BaseCollectionModel[PersonCommitteeRoleList]):
    pass


class PersonShowRoleList(NthpSchema):
    """A person who took a show role, as the role's own index gives them."""

    person: PersonRef = Field(description="The person who took the role")
    role: str = Field(
        description="Canonical name of the role",
        json_schema_extra={"example": "Director"},
    )
    show_count: int = Field(
        description="Number of shows the person took the role on",
        json_schema_extra={"example": 7},
    )


class PersonShowRoleListCollection(BaseCollectionModel[PersonShowRoleList]):
    pass


class Role(NthpSchema):
    """A role held on a show or a committee, aliases folded together."""

    id: str = Field(
        description="ID of the role, slugified from its canonical name",
        json_schema_extra={"example": "publicity_manager"},
    )
    name: str = Field(
        description="Canonical name of the role",
        json_schema_extra={"example": "Publicity Manager"},
    )
    aliases: list[str] = Field(
        default=[],
        description="Other names the role has been authored under",
        json_schema_extra={"example": ["Publicity"]},
    )
    holding_count: int = Field(
        description="Number of times the role has been held",
        json_schema_extra={"example": 42},
    )


class RoleCollection(BaseCollectionModel[Role]):
    pass


class PersonGraduated(YearRef):
    """The academic year a person graduated in, authored or estimated."""

    estimated: bool = Field(
        description="Whether the year is estimated from the person's credits rather "
        "than authored",
        json_schema_extra={"example": False},
    )

    @classmethod
    def from_grad_year(cls, grad_year: int, *, estimated: bool) -> "PersonGraduated":
        """The academic year that ends in the given graduation year."""
        return cls(**dict(YearRef.from_start_year(grad_year - 1)), estimated=estimated)


class PersonIndexItem(NthpSchema):
    """A person as the index of every person gives them."""

    id: str = Field(
        description="ID of the person, slugified from their name",
        json_schema_extra={"example": "fred_bloggs"},
    )
    title: str = Field(
        description="Name of the person", json_schema_extra={"example": "Fred Bloggs"}
    )
    has_bio: bool = Field(
        description="Whether the archive holds a document about the person, as "
        "opposed to knowing them only from the credits they appear in",
        json_schema_extra={"example": True},
    )
    headshot: ImageRef | None = Field(
        default=None, description="The person's headshot, where there is one"
    )
    graduated: PersonGraduated | None = Field(
        default=None,
        description="The academic year the person graduated in, where it is known "
        "or can be estimated",
    )
    submitted: bool = Field(
        description="Whether the person submitted the record themselves",
        json_schema_extra={"example": True},
    )
    submitted_date: FuzzyDate | None = Field(
        default=None,
        description="Date the person submitted the record, where it is known",
        json_schema_extra={"example": "2022-01"},
    )
    show_role_count: int = Field(
        description="Number of shows the person is credited on",
        json_schema_extra={"example": 7},
    )
    committee_role_count: int = Field(
        description="Number of committee positions the person has held",
        json_schema_extra={"example": 2},
    )


class PersonIndexCollection(BaseCollectionModel[PersonIndexItem]):
    pass


class PersonDetail(PersonIndexItem):
    """Everything the archive holds about a person."""

    headshot: Asset | None = Field(  # type: ignore[assignment]
        default=None, description="The person's headshot, where there is one"
    )
    show_roles: list[PersonShowRoles] = Field(
        default=[], description="What the person did, by show"
    )
    committee_roles: list[PersonCommitteeRole] = Field(
        default=[], description="Committee positions the person has held"
    )
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
    trivia: list[Trivia] = Field(
        default=[], description="Trivia submitted by this person"
    )
    content: str | None = Field(
        default=None, description="The person's biography, in HTML"
    )


class PersonCollaborator(NthpSchema):
    """Someone a person worked alongside, and what they worked on together."""

    person: PersonRef = Field(description="The collaborator")
    target_ids: list[str] = Field(
        default=[],
        description="IDs of the shows and academic years they worked on together",
        json_schema_extra={"example": ["2024-25/macbeth"]},
    )


class PersonCollaboratorCollection(BaseCollectionModel[PersonCollaborator]):
    pass


class HistoryRecordImage(NthpSchema):
    """An image illustrating a history record, held outside the asset store."""

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
        default=None,
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

    Search documents are the one place references are flattened to `{entity}Id`
    fields rather than nested refs, and the record's image is a bare `imageId`
    rather than an `ImageRef`: the whole corpus ships to every visitor, so the
    bytes a nested object costs are worth more here than the symmetry.
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
        description="Calendar year the start year's decade begins in",
        json_schema_extra={"example": 2020},
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
    playwright_descriptor: str | None = Field(
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
    people: list[str] = Field(
        default=[],
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
    graduation_year_id: str | None = Field(
        default=None,
        description="ID of the academic year the person graduated in, in YYYY-YY "
        "form; absent where they are yet to graduate or nothing is known",
        json_schema_extra={"example": "2024-25"},
    )
    graduation_year: int | None = Field(
        default=None,
        description="Calendar year the person graduated in",
        json_schema_extra={"example": 2025},
    )
    graduation_decade: int | None = Field(
        default=None,
        description="Calendar year the graduation year's decade begins in",
        json_schema_extra={"example": 2020},
    )
    graduation_estimated: bool | None = Field(
        default=None,
        description="Whether the graduation year is estimated from the person's "
        "credits rather than authored",
        json_schema_extra={"example": False},
    )
    course: list[str] = Field(
        default=[],
        description="Courses the person studied",
        json_schema_extra={"example": ["English"]},
    )
    careers: list[str] = Field(
        default=[],
        description="Careers the person has followed, theatre related or not",
        json_schema_extra={"example": ["Director"]},
    )
    award: str | None = Field(
        default=None,
        description="Award the person received on leaving the theatre, as authored",
        json_schema_extra={"example": "Fellowship"},
    )
    show_roles: list[str] = Field(
        default=[],
        description="Distinct roles the person has taken on a show, crew roles under "
        "their canonical name and acting as `Actor`",
        json_schema_extra={"example": ["Actor", "Director"]},
    )
    committee_roles: list[str] = Field(
        default=[],
        description="Distinct committee positions the person has held, under their "
        "canonical name",
        json_schema_extra={"example": ["Publicity Manager"]},
    )
    show_count: int = Field(
        description="Number of shows the person is credited on",
        json_schema_extra={"example": 7},
    )
    year_ids: list[str] = Field(
        default=[],
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
        description="Calendar year the start year's decade begins in",
        json_schema_extra={"example": 2020},
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
        description="Branch of the repository the API was built from.",
        json_schema_extra={"example": "master"},
    )
    api_version: str = Field(
        title="API Version",
        description="Version of nthp-api that built the API.",
        json_schema_extra={"example": "0.3.0"},
    )
    commit: str | None = Field(
        default=None,
        title="Commit",
        description="Commit of the repository the API was built from, where it was "
        "built by CI.",
        json_schema_extra={"example": "1f0a9c2e0c0a4a1b8d3f6e5c4b3a29180706f5e4"},
    )
    build_number: str | None = Field(
        default=None,
        title="Build Number",
        description="Number of the GitHub Actions run that built the API, where it "
        "was built by one.",
        json_schema_extra={"example": "42"},
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
    person_with_headshot_count: int = Field(
        title="Person with headshot count",
        description="Number of people with a headshot.",
        json_schema_extra={"example": 1234},
    )
    show_with_image_count: int = Field(
        title="Show with image count",
        description="Number of shows with a primary image.",
        json_schema_extra={"example": 1234},
    )
    venue_count: int = Field(
        title="Venue Count",
        description="Number of venues, documented or merely referenced by a show.",
        json_schema_extra={"example": 1234},
    )
    year_count: int = Field(
        title="Year Count",
        description="Number of academic years covered by the archive.",
        json_schema_extra={"example": 85},
    )
    first_year_id: str = Field(
        title="First Year ID",
        description="ID of the earliest academic year covered, in YYYY-YY form.",
        json_schema_extra={"example": "1940-41"},
    )
    latest_year_id: str = Field(
        title="Latest Year ID",
        description="ID of the most recent academic year covered, in YYYY-YY form.",
        json_schema_extra={"example": "2024-25"},
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
