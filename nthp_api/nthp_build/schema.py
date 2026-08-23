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
    """Where a venue is, as a point in decimal degrees."""

    lat: float = Field(
        description="Latitude in decimal degrees",
        examples=[52.9385],
    )
    lon: float = Field(
        description="Longitude in decimal degrees",
        examples=[-1.1957],
    )

    @classmethod
    def from_model(cls, model: models.Location):
        return cls(lat=model.lat, lon=model.lon)


class Link(NthpSchema):
    """A link to a resource beyond the archive: a profile, a review, a news story."""

    type: str = Field(
        description="Type of resource, canonical name where the content repo's "
        "`_data/link-types.yaml` defines the type, otherwise as authored",
        examples=["Review"],
    )
    is_news: bool = Field(
        description="Whether the type is a news type, an article or a review",
        examples=[True],
    )
    href: str | None = Field(
        default=None,
        description="URL of the resource, resolved from the username where the type "
        "templates one",
        examples=["https://twitter.com/nnt_official"],
    )
    href_snapshot: str | None = Field(
        default=None,
        description="URL of the archive.is snapshot of the resource, where one has "
        "been taken",
        examples=["https://archive.is/abc12"],
    )
    username: str | None = Field(
        default=None,
        description="Username on the service, where the type is a service",
        examples=["nnt_official"],
    )
    title: str | None = Field(
        default=None,
        description="Title of the resource, such as the headline of an article",
        examples=["Student theatre at its best"],
    )
    date: FuzzyDate | None = Field(
        default=None,
        description="Date the resource was published, of year, month or day precision",
        examples=["2022-01-31"],
    )
    publisher: str | None = Field(
        default=None,
        description="Name of the publisher, given for news and reviews",
        examples=["Impact Magazine"],
    )
    rating: str | None = Field(
        default=None,
        description="Rating a review gave, written as `x/of_y`",
        examples=["4/5"],
    )
    quote: str | None = Field(
        default=None,
        description="Short quotation summarising the resource",
        examples=["A triumph from start to finish"],
    )
    note: str | None = Field(
        default=None,
        description="Note about the resource, displayed alongside the link",
        examples=["Requires a subscription"],
    )


class ImageRef(NthpSchema):
    """
    An image referenced from a list or a summary, by key and intrinsic size.

    Detail documents carry the full `Asset` instead. Dimensions are absent only
    where SmugMug could not answer for the key.
    """

    id: str = Field(
        description="SmugMug image key",
        examples=["qABC123"],
    )
    width: int | None = Field(
        default=None,
        description="Intrinsic width of the image in pixels",
        examples=[1600],
    )
    height: int | None = Field(
        default=None,
        description="Intrinsic height of the image in pixels",
        examples=[1200],
    )


class Asset(ImageRef):
    """A file the archive holds about a record: an image, a video or a document."""

    type: str = Field(
        description="Kind of asset, one of `album`, `image`, `video` or `other`",
        examples=["image"],
    )
    source: str = Field(
        description="Where the asset is held, `smugmug` or `file`",
        examples=["smugmug"],
    )
    mime_type: str | None = Field(
        default=None,
        description="Mime type of the asset, where one applies",
        examples=["image/jpeg"],
    )
    category: str | None = Field(
        default=None,
        description="What the asset depicts, as authored; poster, flyer, programme "
        "and headshot are the recognised categories",
        examples=["poster"],
    )
    title: str | None = Field(
        default=None,
        description="Title of the asset, as authored",
        examples=["Programme"],
    )
    page: int | None = Field(
        default=None,
        description="Page of the document the asset is, where it is one of several",
        examples=[2],
    )
    uploaded_at: datetime.datetime | None = Field(
        default=None,
        description="When the asset was uploaded to SmugMug, where SmugMug knows",
        examples=["2022-01-01T12:34:45.678901Z"],
    )


class AssetCollection(BaseCollectionModel[Asset]):
    """The images an album holds, in the order SmugMug gives them."""


class PersonRef(NthpSchema):
    """A person credited somewhere, whether or not the archive holds a bio."""

    id: str = Field(
        description="ID of the person",
        examples=["fred_bloggs"],
    )
    title: str = Field(
        description="Name of the person",
        examples=["Fred Bloggs"],
    )
    is_person: bool = Field(
        description="Whether the credit names a person rather than a group",
        examples=[True],
    )
    has_bio: bool = Field(
        description="Whether the archive holds a document about the person, as "
        "opposed to knowing them only from the credits they appear in",
        examples=[True],
    )
    headshot: ImageRef | None = Field(
        default=None, description="The person's headshot, where there is one"
    )


class VenueRef(NthpSchema):
    """A venue a show ran at."""

    id: str = Field(
        description="ID of the venue, slugified from the authored venue name",
        examples=["new-theatre"],
    )
    name: str = Field(
        description="Name of the venue as authored on the show",
        examples=["New Theatre"],
    )


class YearRef(NthpSchema):
    """An academic year, as every year reference gives it."""

    id: str = Field(
        description="ID of the academic year, in YYYY-YY form",
        examples=["2024-25"],
    )
    title: str = Field(
        description="Title of the academic year",
        examples=["2024-25"],
    )
    start_year: int = Field(
        description="Calendar year the academic year starts in",
        examples=[2024],
    )
    grad_year: int = Field(
        description="Calendar year students of this academic year graduate in",
        examples=[2025],
    )
    decade: int = Field(
        description="Calendar year the start year's decade begins in",
        examples=[2020],
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
        examples=["2024-25/macbeth"],
    )
    title: str = Field(description="Title of the show", examples=["Macbeth"])
    year_id: str = Field(
        description="ID of the academic year the show is in, in YYYY-YY form",
        examples=["2024-25"],
    )
    year: int = Field(
        description="Calendar year the academic year starts in",
        examples=[2024],
    )
    primary_image: ImageRef | None = Field(
        default=None, description="Image standing for the show, where there is one"
    )


class ShowDatedRef(ShowRef):
    """A show reference carrying its run, for lists ordered by date."""

    date_start: FuzzyDate | None = Field(
        default=None,
        description="Date the show opened, of year, month or day precision",
        examples=["2024-11-13"],
    )
    date_end: FuzzyDate | None = Field(
        default=None,
        description="Date the show closed, of year, month or day precision",
        examples=["2024-11-16"],
    )


class PlayRef(NthpSchema):
    """A play, the work a show staged."""

    id: str = Field(
        description="ID of the play, slugified from its title",
        examples=["macbeth"],
    )
    title: str = Field(description="Title of the play", examples=["Macbeth"])


class PlaywrightRef(NthpSchema):
    """
    Whoever wrote the work a show staged.

    Every field is absent for a show that was devised, improvised, of unknown
    authorship or written by several hands.
    """

    id: str | None = Field(
        default=None,
        description="ID of the playwright, slugified from their name",
        examples=["william_shakespeare"],
    )
    name: str | None = Field(
        default=None,
        description="Name of the playwright",
        examples=["William Shakespeare"],
    )
    person_id: str | None = Field(
        default=None,
        description="ID of the person the playwright is, where a student wrote it",
        examples=["fred_bloggs"],
    )


class PlaywrightType(Enum):
    """
    How the work a show staged came to be written.

    `playwright` names a writer; `various` is a bill of several writers' work;
    `unknown` is a written work whose author the archive does not know; `devised`
    was made by the company; `improvised` was made on the night.
    """

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
        examples=["by William Shakespeare"],
    )
    student_written: bool = Field(
        description="Whether a student of the university wrote it",
        examples=[False],
    )


class PersonCredit(NthpSchema):
    """A person credited in a role, on a show or on a committee."""

    role: str | None = Field(
        default=None,
        description="Role as authored",
        examples=["Director"],
    )
    person: PersonRef | None = Field(
        default=None, description="The person credited, where the credit names one"
    )
    note: str | None = Field(
        default=None,
        description="Note about the credit, displayed alongside it",
        examples=["Act 2 only"],
    )


class ShowTourDate(NthpSchema):
    """A run of the show at another venue, while on tour."""

    venue: str | None = Field(
        default=None,
        description="Venue the show toured to, as authored",
        examples=["Lakeside Arts"],
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
    """What kind of record a piece of trivia is about; only shows carry trivia."""

    SHOW = "show"


class TriviaTarget(ShowRef):
    """What a piece of trivia is about; only shows carry trivia today."""

    type: TriviaTargetType = Field(description="What kind of record the target is")


class Trivia(NthpSchema):
    """A story or quote submitted about a show."""

    quote: str = Field(
        description="The quote",
        examples=[
            (
                "Every character in this play was portrayed by a "
                "perfectly circular Victoria Sponge"
            )
        ],
    )
    submitted_date: FuzzyDate | None = Field(
        default=None,
        description="The date the quote was submitted, of year, month or day "
        "precision; absent where it is likely pulled from the programme or another "
        "source",
        examples=["2022-01"],
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
        examples=["2024-25/macbeth"],
    )
    title: str = Field(description="Title of the show", examples=["Macbeth"])
    year_id: str = Field(
        description="ID of the academic year the show is in, in YYYY-YY form",
        examples=["2024-25"],
    )
    year: int = Field(
        description="Calendar year the academic year starts in",
        examples=[2024],
    )
    season: str = Field(
        description="Season as authored on the show",
        examples=["In House"],
    )
    season_id: str | None = Field(
        default=None,
        description="ID of the season, aliases merged",
        examples=["in-house"],
    )
    venue: VenueRef | None = Field(
        default=None, description="Venue the show ran at, where one is authored"
    )
    date_start: FuzzyDate | None = Field(
        default=None,
        description="Date the show opened, of year, month or day precision",
        examples=["2024-11-13"],
    )
    date_end: FuzzyDate | None = Field(
        default=None,
        description="Date the show closed, of year, month or day precision",
        examples=["2024-11-16"],
    )
    primary_image: ImageRef | None = Field(
        default=None, description="Image standing for the show, where there is one"
    )
    playwright_descriptor: str | None = Field(
        default=None,
        description="How the show's authorship reads",
        examples=["by William Shakespeare"],
    )


class ShowIndexCollection(BaseCollectionModel[ShowIndexItem]):
    """Every show in the archive's canonical order: year, then season, then date."""


class ShowList(ShowIndexItem):
    """A show as the lists embedded in year, season and venue documents give it."""

    playwright: PlaywrightShow | None = Field(
        default=None, description="How the show came to be written"
    )
    adaptor: str | None = Field(
        default=None,
        description="Who adapted the work, as authored",
        examples=["Fred Bloggs"],
    )
    devised: bool = Field(
        description="Whether the show was devised rather than written",
        examples=[False],
    )


class ShowDetail(ShowList):
    """Everything the archive holds about a show."""

    play: PlayRef | None = Field(
        default=None, description="The play staged, where the show staged one"
    )
    translator: str | None = Field(
        default=None,
        description="Who translated the work, as authored",
        examples=["Fred Bloggs"],
    )
    company: str | None = Field(
        default=None,
        description="Company that staged the show, where it was not the theatre",
        examples=["Nottingham New Theatre"],
    )
    period: str | None = Field(
        default=None,
        description="Period the show is set in, as authored",
        examples=["Victorian"],
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
    """
    Shows running on one day of the year, in the archive's canonical show order.

    Shows dated only to the month or the year cannot be placed on a day, so they
    appear on none.
    """


class PosterItem(ShowRef):
    """A show's primary image, for picking posters to display."""

    primary_image: ImageRef = Field(description="The show's primary image")


class PosterCollection(BaseCollectionModel[PosterItem]):
    """Every show with a primary image, in the archive's canonical show order."""


class SeasonList(NthpSchema):
    """A season as the index of seasons gives it."""

    id: str = Field(
        description="ID of the season, slugified from its canonical name",
        examples=["in-house"],
    )
    name: str = Field(
        description="Canonical name of the season",
        examples=["In House"],
    )
    aliases: list[str] = Field(
        default=[],
        description="Other names the season has been authored under",
        examples=[["UNCUT"]],
    )
    show_count: int = Field(
        description="Number of shows in the season",
        examples=[42],
    )


class SeasonListCollection(BaseCollectionModel[SeasonList]):
    """Every season, in the order the API defines them."""


class SeasonDetail(SeasonList):
    """A season and its shows; seasons span academic years, so shows run by date."""

    shows: list[ShowList] = Field(default=[], description="Shows in the season")


class VenueList(NthpSchema):
    """A venue as the index of venues gives it."""

    id: str = Field(
        description="ID of the venue, slugified from the authored venue name",
        examples=["new-theatre"],
    )
    name: str = Field(
        description="Name of the venue",
        examples=["New Theatre"],
    )
    show_count: int = Field(
        description="Number of shows at the venue",
        examples=[42],
    )
    group: str | None = Field(
        default=None,
        description="Name of the group the venue belongs to, where shows give one, "
        "for grouping venues such as Edinburgh's C venues",
        examples=["C venues"],
    )
    has_record: bool = Field(
        description="Whether the venue is documented in the archive; venues only "
        "referenced by shows are stubs, carrying no details beyond name and shows",
        examples=[True],
    )
    sentinel: bool = Field(
        description="Whether the venue stands in for the absence of a venue, such as "
        "an unknown venue or an online performance",
        examples=[False],
    )
    built: int | None = Field(
        default=None,
        description="Year the venue was built",
        examples=[1965],
    )
    location: Location | None = Field(
        default=None, description="Where the venue is, where it is known"
    )
    city: str | None = Field(
        default=None,
        description="City the venue is in",
        examples=["Nottingham"],
    )


class VenueDetail(VenueList):
    """
    Everything the archive holds about a venue.

    A venue only referenced by shows is a stub: it carries no assets, links or
    description, just its name and the shows that ran there.
    """

    assets: list[Asset] = Field(default=[], description="Images held of the venue")
    links: list[Link] = Field(
        default=[], description="Links to the venue's own site and other resources"
    )
    shows: list[ShowList] = Field(default=[], description="Shows that ran at the venue")
    content: str | None = Field(
        default=None, description="The venue's description, in HTML"
    )


class VenueCollection(BaseCollectionModel[VenueList]):
    """Every venue, documented or merely referenced by a show, ordered by id."""


class PlaywrightListItem(PlaywrightRef):
    """A writer and every show of their work, oldest first."""

    shows: list[ShowDatedRef] = Field(
        default=[], description="Shows of the playwright's work"
    )


class PlaywrightCollection(BaseCollectionModel[PlaywrightListItem]):
    """Every writer of a staged work, by id, named as their latest show spells them."""


class PlayListItem(PlayRef):
    """A play and every show of it, oldest first."""

    playwright: PlaywrightRef = Field(description="Who wrote the play")
    shows: list[ShowDatedRef] = Field(default=[], description="Shows of the play")


class PlayCollection(BaseCollectionModel[PlayListItem]):
    """Every play staged, one entry per play and writer, ordered by play id."""


class YearList(YearRef):
    """An academic year as the index of years gives it."""

    show_count: int = Field(
        description="Number of shows in the academic year",
        examples=[42],
    )


class YearListCollection(BaseCollectionModel[YearList]):
    """Every academic year the archive covers, earliest first."""


class YearDetail(YearList):
    """Everything the archive holds about an academic year."""

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
    """Which credit list a show role comes from: `cast` acted, `crew` made it."""

    CAST = "cast"
    CREW = "crew"


class PersonShowRoleItem(NthpSchema):
    """One role a person took on a show."""

    role: str | None = Field(
        default=None,
        description="Role as authored, absent for a cast credit naming no part",
        examples=["Director"],
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
        examples=["Publicity Manager"],
    )


class PersonCommitteeRoleList(NthpSchema):
    """A person who held a committee position, as the role's own index gives them."""

    person: PersonRef = Field(description="The person who held the position")
    year: YearRef = Field(description="The academic year the position was held in")
    role: str = Field(
        description="Position as authored",
        examples=["Publicity Manager"],
    )


class PersonCommitteeRoleListCollection(BaseCollectionModel[PersonCommitteeRoleList]):
    """
    Everyone who has held one committee position, earliest academic year first.

    Aliases of the position are folded in, and a person appears once for every year
    they held it.
    """


class PersonShowRoleList(NthpSchema):
    """A person who took a show role, as the role's own index gives them."""

    person: PersonRef = Field(description="The person who took the role")
    role: str = Field(
        description="Canonical name of the role",
        examples=["Director"],
    )
    show_count: int = Field(
        description="Number of shows the person took the role on",
        examples=[7],
    )


class PersonShowRoleListCollection(BaseCollectionModel[PersonShowRoleList]):
    """
    Everyone who has taken one show role, ordered by person id.

    Aliases of the role are folded in, and a person appears once however many shows
    they took it on.
    """


class Role(NthpSchema):
    """A role held on a show or a committee, aliases folded together."""

    id: str = Field(
        description="ID of the role, slugified from its canonical name",
        examples=["publicity_manager"],
    )
    name: str = Field(
        description="Canonical name of the role",
        examples=["Publicity Manager"],
    )
    aliases: list[str] = Field(
        default=[],
        description="Other names the role has been authored under",
        examples=[["Publicity"]],
    )
    holding_count: int = Field(
        description="Number of times the role has been held",
        examples=[42],
    )


class RoleCollection(BaseCollectionModel[Role]):
    """
    Roles of one kind, show or committee.

    Crew roles come in the order the content repo defines them, committee roles
    alphabetically; roles named `unknown` are left out of both.
    """


class PersonGraduated(YearRef):
    """The academic year a person graduated in, authored or estimated."""

    estimated: bool = Field(
        description="Whether the year is estimated from the person's credits rather "
        "than authored",
        examples=[False],
    )

    @classmethod
    def from_grad_year(cls, grad_year: int, *, estimated: bool) -> "PersonGraduated":
        """The academic year that ends in the given graduation year."""
        return cls(**dict(YearRef.from_start_year(grad_year - 1)), estimated=estimated)


class PersonIndexItem(NthpSchema):
    """A person as the index of every person gives them."""

    id: str = Field(
        description="ID of the person, slugified from their name",
        examples=["fred_bloggs"],
    )
    title: str = Field(description="Name of the person", examples=["Fred Bloggs"])
    has_bio: bool = Field(
        description="Whether the archive holds a document about the person, as "
        "opposed to knowing them only from the credits they appear in",
        examples=[True],
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
        examples=[True],
    )
    submitted_date: FuzzyDate | None = Field(
        default=None,
        description="Date the person submitted the record, where it is known",
        examples=["2022-01"],
    )
    show_role_count: int = Field(
        description="Number of shows the person is credited on",
        examples=[7],
    )
    committee_role_count: int = Field(
        description="Number of committee positions the person has held",
        examples=[2],
    )


class PersonIndexCollection(BaseCollectionModel[PersonIndexItem]):
    """Everyone the archive gives a document to, with a bio or without, by id."""


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
        examples=[["English"]],
    )
    award: str | None = Field(
        default=None,
        description="Award the person received on leaving the theatre, as authored; "
        "usually Fellowship, Commendation, Merit or Union Prize, but not held to "
        "that set",
        examples=["Fellowship"],
    )
    careers: list[str] = Field(
        default=[],
        description="Careers the person has followed, theatre related or not, as "
        "authored; the content repo's `_data/careers.yaml` lists the recognised "
        "theatre careers but records are not held to it",
        examples=[["Director"]],
    )
    student: bool = Field(
        description="Whether the person is likely still a student, worked out from "
        "their graduation year and the date the API was built, so it goes stale "
        "between builds",
        examples=[False],
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
        examples=[["2024-25/macbeth"]],
    )


class PersonCollaboratorCollection(BaseCollectionModel[PersonCollaborator]):
    """Everyone one person worked alongside, ordered by collaborator id."""


class HistoryRecordImage(NthpSchema):
    """An image illustrating a history record, held outside the asset store."""

    href: str = Field(
        description="URL of the image",
        examples=["https://photos.newtheatre.org.uk/i-abc123.jpg"],
    )
    alt: str = Field(
        description="Short caption describing the image",
        examples=["The old auditorium"],
    )


class HistoryRecord(NthpSchema):
    """A moment in the theatre's history, as the content repo's timeline records it."""

    year: str = Field(
        description="Short description of the year of the record, "
        "e.g. '1940' / '1940s'",
        examples=["1940s"],
    )
    year_id: str | None = Field(
        default=None,
        description="Exact year ID of the record, in YYYY-YY form",
        examples=["1940-41"],
    )
    title: str = Field(
        description="Title of the record",
        examples=["Theatre built"],
    )
    description: str = Field(
        description="Description of the record, in HTML",
        examples=["<p>Theatre built in 1940</p>"],
    )
    image: HistoryRecordImage | None = Field(
        default=None, description="Image illustrating the record, where there is one"
    )


class HistoryRecordCollection(BaseCollectionModel[HistoryRecord]):
    """The theatre's timeline, in the order the content repo records it."""


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
        examples=["Macbeth"],
    )
    id: str = Field(
        description="ID of the record, as its own document is keyed by",
        examples=["2024-25/macbeth"],
    )
    image_id: str | None = Field(
        default=None,
        description="Image illustrating the record, where there is one",
        examples=["abc12"],
    )


class SearchDocumentShow(SearchDocumentBase):
    """A show, the archive's principal record."""

    type: Literal[SearchDocumentType.SHOW] = Field(
        description="What the document describes, always `show`"
    )
    year_id: str = Field(
        description="ID of the academic year the show ran in, in YYYY-YY form",
        examples=["2024-25"],
    )
    year: int = Field(
        description="Calendar year the academic year starts in",
        examples=[2024],
    )
    decade: int = Field(
        description="Calendar year the start year's decade begins in",
        examples=[2020],
    )
    season: str = Field(
        description="Season as authored on the show",
        examples=["Autumn Season"],
    )
    season_id: str | None = Field(
        default=None,
        description="ID of the season, where the authored season is a known one",
        examples=["autumn_season"],
    )
    venue_id: str | None = Field(
        default=None,
        description="ID of the venue the show ran at",
        examples=["nottingham-new-theatre"],
    )
    venue_name: str | None = Field(
        default=None,
        description="Name of the venue as authored on the show",
        examples=["Nottingham New Theatre"],
    )
    date_start: FuzzyDate | None = Field(
        default=None,
        description="Date the show opened, of year, month or day precision",
        examples=["2024-11-13"],
    )
    playwright_descriptor: str | None = Field(
        default=None,
        description="How the show describes its authorship, e.g. `by Shakespeare`, "
        "`Devised` or `Various Writers`",
        examples=["by William Shakespeare"],
    )
    company: str | None = Field(
        default=None,
        description="Company that staged the show, where it was not the theatre",
        examples=["Nottingham New Theatre"],
    )
    people: list[str] = Field(
        default=[],
        description="Names of everyone credited on the show, cast and crew alike",
        examples=[["Fred Bloggs"]],
    )
    plaintext: str | None = Field(
        default=None,
        description="The show's description, markup stripped",
        examples=["A tragedy of ambition."],
    )


class SearchDocumentPerson(SearchDocumentBase):
    """Anyone credited on a show or committee, whether or not they have a bio."""

    type: Literal[SearchDocumentType.PERSON] = Field(
        description="What the document describes, always `person`"
    )
    has_bio: bool = Field(
        description="Whether the archive holds a document about the person, as "
        "opposed to knowing them only from the credits they appear in",
        examples=[True],
    )
    graduation_year_id: str | None = Field(
        default=None,
        description="ID of the academic year the person graduated in, in YYYY-YY "
        "form; absent where they are yet to graduate or nothing is known",
        examples=["2024-25"],
    )
    graduation_year: int | None = Field(
        default=None,
        description="Calendar year the person graduated in",
        examples=[2025],
    )
    graduation_decade: int | None = Field(
        default=None,
        description="Calendar year the graduation year's decade begins in",
        examples=[2020],
    )
    graduation_estimated: bool | None = Field(
        default=None,
        description="Whether the graduation year is estimated from the person's "
        "credits rather than authored",
        examples=[False],
    )
    course: list[str] = Field(
        default=[],
        description="Courses the person studied",
        examples=[["English"]],
    )
    careers: list[str] = Field(
        default=[],
        description="Careers the person has followed, theatre related or not",
        examples=[["Director"]],
    )
    award: str | None = Field(
        default=None,
        description="Award the person received on leaving the theatre, as authored",
        examples=["Fellowship"],
    )
    show_roles: list[str] = Field(
        default=[],
        description="Distinct roles the person has taken on a show, crew roles under "
        "their canonical name and acting as `Actor`",
        examples=[["Actor", "Director"]],
    )
    committee_roles: list[str] = Field(
        default=[],
        description="Distinct committee positions the person has held, under their "
        "canonical name",
        examples=[["Publicity Manager"]],
    )
    show_count: int = Field(
        description="Number of shows the person is credited on",
        examples=[7],
    )
    year_ids: list[str] = Field(
        default=[],
        description="IDs of the academic years the person is credited in, whether "
        "on a show or a committee",
        examples=[["2023-24", "2024-25"]],
    )
    plaintext: str | None = Field(
        default=None,
        description="The person's biography, markup stripped",
        examples=["Fred read English and directed a lot."],
    )


class SearchDocumentVenue(SearchDocumentBase):
    """A venue, whether or not the archive holds a document about it."""

    type: Literal[SearchDocumentType.VENUE] = Field(
        description="What the document describes, always `venue`"
    )
    city: str | None = Field(
        default=None,
        description="City the venue is in, where the archive holds a document for it",
        examples=["Nottingham"],
    )
    show_count: int = Field(
        description="Number of shows that ran at the venue",
        examples=[42],
    )
    plaintext: str | None = Field(
        default=None,
        description="The venue's description, markup stripped",
        examples=["A studio theatre on University Park."],
    )


class SearchDocumentYear(SearchDocumentBase):
    """An academic year."""

    type: Literal[SearchDocumentType.YEAR] = Field(
        description="What the document describes, always `year`"
    )
    decade: int = Field(
        description="Calendar year the start year's decade begins in",
        examples=[2020],
    )
    show_count: int = Field(
        description="Number of shows in the academic year",
        examples=[42],
    )


SearchDocument = Annotated[
    SearchDocumentShow
    | SearchDocumentPerson
    | SearchDocumentVenue
    | SearchDocumentYear,
    Field(discriminator="type"),
]


class SearchDocumentCollection(BaseCollectionModel[SearchDocument]):
    """The whole search corpus, ordered by type then id."""


class SearchDocumentShowCollection(BaseCollectionModel[SearchDocumentShow]):
    """The show documents of the search corpus, ordered by id."""


class SearchDocumentPersonCollection(BaseCollectionModel[SearchDocumentPerson]):
    """The person documents of the search corpus, ordered by id."""


class SearchDocumentVenueCollection(BaseCollectionModel[SearchDocumentVenue]):
    """The venue documents of the search corpus, ordered by id."""


class SearchDocumentYearCollection(BaseCollectionModel[SearchDocumentYear]):
    """The year documents of the search corpus, ordered by id."""


class SiteStats(NthpSchema):
    """What the archive holds and how it was built, as of the last build."""

    build_time: datetime.datetime = Field(
        title="Build Time",
        description="When was the API built, in UTC.",
        examples=["2022-01-01T12:34:45.678901Z"],
    )
    branch: str = Field(
        description="Branch of the repository the API was built from.",
        examples=["master"],
    )
    api_version: str = Field(
        title="API Version",
        description="Version of nthp-api that built the API.",
        examples=["0.3.0"],
    )
    commit: str | None = Field(
        default=None,
        title="Commit",
        description="Commit of the repository the API was built from, where it was "
        "built by CI.",
        examples=["1f0a9c2e0c0a4a1b8d3f6e5c4b3a29180706f5e4"],
    )
    build_number: str | None = Field(
        default=None,
        title="Build Number",
        description="Number of the GitHub Actions run that built the API, where it "
        "was built by one.",
        examples=["42"],
    )
    show_count: int = Field(
        title="Show Count",
        description="Number of shows in the database.",
        examples=[1234],
    )
    person_count: int = Field(
        title="Person Count",
        description="Number of people in the database.",
        examples=[1234],
    )
    person_with_bio_count: int = Field(
        title="Person with bio count",
        description="Number of people with bio records.",
        examples=[1234],
    )
    person_with_headshot_count: int = Field(
        title="Person with headshot count",
        description="Number of people with a headshot.",
        examples=[1234],
    )
    show_with_image_count: int = Field(
        title="Show with image count",
        description="Number of shows with a primary image.",
        examples=[1234],
    )
    venue_count: int = Field(
        title="Venue Count",
        description="Number of venues, documented or merely referenced by a show.",
        examples=[1234],
    )
    year_count: int = Field(
        title="Year Count",
        description="Number of academic years covered by the archive.",
        examples=[85],
    )
    first_year_id: str = Field(
        title="First Year ID",
        description="ID of the earliest academic year covered, in YYYY-YY form.",
        examples=["1940-41"],
    )
    latest_year_id: str = Field(
        title="Latest Year ID",
        description="ID of the most recent academic year covered, in YYYY-YY form.",
        examples=["2024-25"],
    )
    credit_count: int = Field(
        title="Credit Count",
        description="Number of credits, inc. cast/crew/committee roles.",
        examples=[1234],
    )
    trivia_count: int = Field(
        title="Trivia Count",
        description="Number of bits of trivia or stories.",
        examples=[1234],
    )
    search_document_count: int = Field(
        title="Search Document Count",
        description="Number of documents in the search corpus, shows, people, venues "
        "and years together.",
        examples=[1234],
    )
