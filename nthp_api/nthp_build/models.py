"""The models for ingesting data"""

import re
from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic_collections import BaseCollectionModel
from slugify import slugify

from nthp_api.nthp_build import years
from nthp_api.nthp_build.fields import FuzzyDate, PermissiveStr


class NthpModel(BaseModel):
    """
    Base for every ingest model.

    Unknown keys are rejected: a key the models do not know is a key the API never
    emits, and every such key found so far has been a typo or a dead convention.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


ALLOWED_URL_SCHEMES = frozenset({"http", "https", "mailto"})

RATING_PATTERN = re.compile(r"^(?P<score>\d+(\.\d+)?)\s*(/\s*(?P<outof>\d+))?$")
DEFAULT_RATING_OUT_OF = 5


def editor_comment() -> Any:
    """`comment` is on nearly every shape, and says the same thing on each."""
    return Field(
        default=None,
        title="Editors' comment",
        description="A note to other editors about the record. Never published.",
    )


class Link(NthpModel):
    """A link to a resource elsewhere: a profile, a review, a news story."""

    type: str = Field(
        title="Type of the resource",
        description=(
            "Common types are defined in `_data/link-types.yaml`. A type with no "
            "definition still works, but gets no icon and no news handling."
        ),
        examples=["facebook", "review"],
    )
    href: str | None = Field(
        default=None,
        title="URL of the resource",
        description=(
            "Only the `http`, `https` and `mailto` schemes are accepted. Omit where "
            "the link type builds its own href from `username`."
        ),
        examples=["https://www.thestage.co.uk/reviews/a-review"],
    )
    author: PermissiveStr | None = Field(
        default=None,
        title="Who wrote the piece linked to",
        description="Ingested but not published, as no consumer asks for it yet.",
    )
    snapshot: str | None = Field(
        default=None,
        title="Archive snapshot reference",
        description=(
            "The five-character [archive.is](https://archive.is) snapshot reference, "
            "which is case-sensitive."
        ),
        examples=["aBc1D"],
    )
    username: PermissiveStr | None = Field(
        default=None,
        title="Username on a service",
        description=(
            "Where the type defines an `href` template in `_data/link-types.yaml`, "
            "give the username here instead of an `href`."
        ),
    )
    title: PermissiveStr | None = Field(
        default=None,
        title="Title of the resource",
        description=(
            "The headline of a news article or the title of a page. Include it only "
            "where it says something the type does not."
        ),
    )
    date: FuzzyDate | None = Field(
        default=None,
        title="Date the resource was published",
        description=(
            "`YYYY-MM-DD`, or `YYYY-MM` or `YYYY` where the day or month is unknown."
        ),
    )
    publisher: PermissiveStr | None = Field(
        default=None,
        title="Name of the publisher",
        description="Useful on news articles, expected on reviews.",
        examples=["Impact Magazine"],
    )
    rating: PermissiveStr | None = Field(
        default=None,
        title="Rating a review gave",
        description=(
            "A score out of a total, written `4/5` or `8/10`. A bare score is read "
            "as out of five."
        ),
        examples=["4/5", "8/10"],
    )
    quote: PermissiveStr | None = Field(
        default=None,
        title="Short quote from the resource",
        description="A sentence or so from a review or news story.",
    )
    note: PermissiveStr | None = Field(
        default=None,
        title="A visible note about the resource",
        description="Shown alongside the link.",
    )
    comment: PermissiveStr | None = editor_comment()

    @field_validator("href")
    @classmethod
    def require_allowed_url_scheme(cls, value: str | None) -> str | None:
        """
        Consumers put these straight in an `href`, so a `javascript:` URL from
        authored content is the same class of problem as a script tag in a body.
        """
        if value is None:
            return None
        scheme, separator, _rest = value.partition(":")
        if not separator or "/" in scheme or scheme == "":
            return value  # Relative URL, no scheme to check
        if scheme.lower() not in ALLOWED_URL_SCHEMES:
            raise ValueError(f"Disallowed URL scheme {scheme!r}")
        return value

    @field_validator("rating", mode="before")
    @classmethod
    def require_rating_in_range(cls, value: object) -> object:
        """
        Ratings are authored as a score out of a total, e.g. `4/5` or `8/10`.

        A bare score is read as out of five, as the archive's own star ratings are.
        """
        if value is None:
            return None
        if isinstance(value, int | float):
            value = str(value)
        if not isinstance(value, str):
            raise ValueError(f"Rating {value!r} is not a score")  # noqa: TRY004
        if not value.strip():
            return None
        match = RATING_PATTERN.match(value.strip())
        if match is None:
            raise ValueError(f"Rating {value!r} is not a score or a score out of one")
        out_of = (
            int(match["outof"]) if match["outof"] is not None else DEFAULT_RATING_OUT_OF
        )
        if not 0 <= float(match["score"]) <= out_of:
            raise ValueError(f"Rating {value!r} is outside 0 to {out_of}")
        return value


class Award(StrEnum):
    """
    The awards the archive is known to hand out on leaving the theatre.

    Not exhaustive: `Person.award` takes any string, as new awards turn up in the
    content before they turn up here. These members exist so the years can be
    indexed on the two that get their own list.
    """

    FELLOWSHIP = "Fellowship"
    COMMENDATION = "Commendation"
    MERIT = "Merit"
    UNION_PRIZE = "Union Prize"


class Location(NthpModel):
    """Where a venue is, as decimal degrees, for a map marker."""

    lat: float = Field(title="Latitude", examples=[52.9385])
    lon: float = Field(title="Longitude", examples=[-1.1959])


class PersonRef(NthpModel):
    """One credit: who did what, on a show or a committee."""

    role: PermissiveStr | None = Field(
        default=None,
        title="Name of the role",
        description=(
            "A part played, a crew role, or a committee position. Crew roles are "
            "defined in `_data/roles.yaml`. Use `unknown` where the role is not "
            "known."
        ),
        examples=["Director", "Macbeth"],
    )
    name: str | None = Field(
        default=None,
        title="The person's name",
        description=(
            "Formatted `Firstname Lastname`, spelled the same way in every credit, "
            "as the spelling makes their id. Use `unknown` where the name is not "
            "known."
        ),
        examples=["Fred Bloggs"],
    )
    note: PermissiveStr | None = Field(
        default=None,
        title="An optional note",
        description=(
            "Shown after the role. Useful where clarification is needed, such as "
            "which half of a double bill the credit is for."
        ),
    )
    person: bool = Field(
        default=True,
        title="Is a New Theatre person",
        description=(
            "Set `false` for entries that are not people — companies, departments, "
            "external organisations — which stops a person record being made."
        ),
    )
    comment: PermissiveStr | None = editor_comment()


class PersonRole(NthpModel):
    """A credit once the loader has resolved the person behind it. Not authored."""

    person_id: str | None = None
    person_name: str | None = None
    role: PermissiveStr | None = None
    note: PermissiveStr | None = None
    is_person: bool = True
    comment: PermissiveStr | None = None


class ShowCanonical(NthpModel):
    """The play as it is catalogued elsewhere, where the show renames it."""

    title: PermissiveStr | None = Field(
        default=None,
        title="Canonical title of the play",
        examples=["A Midsummer Night's Dream"],
    )
    playwright: str | None = Field(
        default=None,
        title="Canonical name of the playwright",
        examples=["William Shakespeare"],
    )


class Asset(NthpModel):
    """An image, video or file belonging to a show or a person."""

    type: str = Field(
        title="Type of asset",
        description=(
            "Lowercase. Only `poster`, `flyer`, `programme` and `headshot` are "
            "categorised; anything else cannot be chosen as a show's main image."
        ),
        examples=["poster", "flyer", "programme", "photo"],
    )
    image: str | None = Field(
        default=None,
        title="SmugMug id of the image",
        description="Exactly one of `image`, `video` or `filename` is required.",
    )
    video: str | None = Field(
        default=None,
        title="SmugMug id of the video",
        description="Exactly one of `image`, `video` or `filename` is required.",
    )
    filename: str | None = Field(
        default=None,
        title="Filename of a non-image asset, such as a PDF",
        description=(
            "Looked up under `assets/for_shows/`. Exactly one of `image`, `video` "
            "or `filename` is required, and `filename` also requires a `title`."
        ),
    )
    title: PermissiveStr | None = Field(
        default=None,
        title="Asset title",
        description=(
            "Shown where the asset cannot be rendered, and for videos. Required "
            "with `filename`."
        ),
    )
    page: int | None = Field(
        default=None,
        title="Orders assets within a type",
        description=(
            "For a programme, the page number, the front page being `1`. For a "
            "single-sheet flyer, the front is `1` and the back `2`. Not needed for "
            "multipage files such as PDFs."
        ),
    )
    display_image: bool = Field(
        default=False,
        title="Force this image to be the show's main image",
        description=(
            "Overrides the usual order of precedence — posters, flyers, then "
            "programmes. Only an `image` asset can carry it."
        ),
    )
    comment: PermissiveStr | None = editor_comment()

    @model_validator(mode="before")
    @classmethod
    def require_image_xor_video_xor_filename(cls, values: dict) -> dict:
        if (
            sum(
                (
                    1 if values.get("image") else 0,
                    1 if values.get("video") else 0,
                    1 if values.get("filename") else 0,
                )
            )
            != 1
        ):
            raise ValueError("Must have exactly one of image, video, or filename")
        return values

    @field_validator("type")
    @classmethod
    def slugify_type(cls, value: str) -> str:
        return slugify(value)

    @model_validator(mode="after")
    def require_title_with_filename(self) -> "Asset":
        if self.filename is not None and self.title is None:
            raise ValueError("title is required if filename is provided")
        return self

    @model_validator(mode="after")
    def display_image_only_for_images(self) -> "Asset":
        if self.display_image and not self.image:
            raise ValueError("Can only set display_image for images")
        return self


class Trivia(NthpModel):
    """An anecdote or short story submitted about a show."""

    quote: str = Field(
        title="The anecdote itself",
        description="Markdown is supported.",
    )
    name: str | None = Field(
        default=None,
        title="Name of the submitter",
        description=(
            "Formatted `Firstname Lastname`. The trivia is only credited where the "
            "name matches someone the archive knows."
        ),
    )
    submitted: FuzzyDate | None = Field(
        default=None,
        title="Date the anecdote was submitted",
        description="`YYYY-MM-DD`.",
    )


class TourDate(NthpModel):
    """One leg of a tour the show went on, such as NSDF."""

    venue: PermissiveStr | None = Field(
        default=None,
        title="Venue this leg played",
    )
    date_start: FuzzyDate | None = Field(
        default=None,
        title="Date of the first performance of this leg",
    )
    date_end: FuzzyDate | None = Field(
        default=None,
        title="Date of the last performance of this leg",
    )
    note: PermissiveStr | None = Field(
        default=None,
        title="A note about this leg",
        description="Also accepted as `notes`.",
    )
    comment: PermissiveStr | None = editor_comment()

    @model_validator(mode="before")
    @classmethod
    def accept_notes_alias(cls, values: dict) -> dict:
        if isinstance(values, dict) and "notes" in values:
            values = dict(values)
            values["note"] = values.pop("notes")
        return values


class Show(NthpModel):
    """One production, in `_shows/<YY_YY>/<name>.md`."""

    id: str = Field(
        title="Show identifier",
        description=(
            "Taken from the filename; set it only to keep a URL that the filename "
            "would change."
        ),
    )
    title: str = Field(
        title="Show title",
        description=(
            "The title of this production, which may differ from the title of the "
            "play — see `canonical`."
        ),
        examples=["Macbeth"],
    )
    playwright: str | None = Field(
        default=None,
        title="Full name of the playwright",
        description=(
            "Omit where the show is devised or improvised; set to `various` for a "
            "compilation."
        ),
        examples=["William Shakespeare"],
    )

    devised: str | bool = Field(
        default=False,
        title="The show was devised",
        description=(
            "`true`, or a descriptor: `Cast and Crew` renders as “Devised by Cast "
            "and Crew”. Omit where there is a playwright."
        ),
    )

    @field_validator("devised")
    @classmethod
    def handle_devised_strings(cls, value: str | bool) -> str | bool:
        if isinstance(value, str):
            if value.lower() == "true":
                return True
            if value.lower() == "false":
                return False
        return value

    improvised: bool = Field(
        default=False,
        title="The show was fully improvised",
        description=(
            "For wholly improvised shows, not scripted shows with improvised "
            "elements. Omit where false."
        ),
    )
    playwright_alias: str | None = Field(
        default=None,
        title="Student name of the playwright",
        description=(
            "Where a student playwright writes under an alias, their student name, "
            "so the generated crew credit attributes them. Needs the show to "
            "generate a student writing credit, so it needs `student_written`."
        ),
    )
    playwright_false: bool = Field(
        default=False,
        title="Exclude the student playwright from the crew list",
        description=(
            "Only meaningful with `student_written`. Use it where the writer is "
            "already credited by hand in `crew`."
        ),
    )
    adaptor: str | None = Field(
        default=None,
        title="Full name of the adaptor",
        description="Rendered as “Adapted by …”.",
    )
    translator: str | None = Field(
        default=None,
        title="Full name of the translator",
        description="Rendered as “Translated by …”.",
    )
    canonical: list[ShowCanonical] = Field(
        default=[],
        title="Canonical titles and playwrights",
        description=(
            "For reverse lookup where this production renames the play or credits "
            "the writer differently."
        ),
    )
    student_written: bool = Field(
        default=False,
        title="Written by a New Theatre member",
        description=(
            "The adaptor, translator or playwright — in that order of precedence — "
            "is then given a crew credit and a person page. Suppress that with "
            "`playwright_false`."
        ),
    )
    company: PermissiveStr | None = Field(
        default=None,
        title="Name of the company",
        description="Non-New Theatre shows only.",
    )
    company_sort: PermissiveStr | None = Field(
        default=None,
        title="Primary name for the company",
        description=(
            "Groups a company whose name has changed over time. Use the name it "
            "had at the time of the show in `company`, and the primary name here."
        ),
    )
    period: str | None = Field(
        default=None,
        title="Period of the year the show ran in",
        description="Omit where unknown.",
        examples=["Autumn", "Spring", "Edinburgh"],
    )
    season: str = Field(
        title="Season the show belongs to",
        description=(
            "A season the site knows; anything else puts the show in no season index."
        ),
        examples=[
            "In House",
            "Fringe",
            "External",
            "StuFF",
            "Edinburgh",
            "Lakeside",
            "Fundraiser",
            "IUDF",
            "Unscripted",
            "Online",
        ],
    )
    season_sort: int | None = Field(
        default=None,
        title="Order the show comes in within its year",
        description=(
            "Multiples of ten, so shows can be inserted later. Roughly: Autumn "
            "starts at 30, Spring at 200 and Edinburgh at 400."
        ),
        examples=[30, 40],
    )
    venue: PermissiveStr | None = Field(
        default=None,
        title="Venue the show was performed in",
        description=(
            "The name makes the venue's id, so spell it identically across shows."
        ),
        examples=["Nottingham New Theatre"],
    )
    venue_sort: PermissiveStr | None = Field(
        default=None,
        title="Group of venues the venue belongs to",
        description=(
            "Groups the show with others sharing the sort — C cubed, C nova and C "
            "soco are all C venues. Does nothing without a `venue`."
        ),
    )
    date_start: FuzzyDate | None = Field(
        default=None,
        title="Date of the first performance",
        description=(
            "`YYYY-MM-DD`, and within the academic year the show is filed under."
        ),
    )
    date_end: FuzzyDate | None = Field(
        default=None,
        title="Date of the last performance",
        description="`YYYY-MM-DD`. Omit where the show ran for one day.",
    )
    tour: list[TourDate] = Field(
        default=[],
        title="Legs of a tour the show went on",
        description=(
            "A show taken to Edinburgh gets its own show under the Edinburgh "
            "period rather than a tour entry."
        ),
    )
    trivia: list[Trivia] = Field(
        default=[],
        title="Anecdotes and short stories about the show",
    )
    cast: list[PersonRef] = Field(default=[], title="Cast members")
    crew: list[PersonRef] = Field(
        default=[],
        title="Crew members",
        description=(
            "The student writer's credit is generated, so it does not need writing "
            "out here."
        ),
    )
    cast_incomplete: bool = Field(
        default=False,
        title="The cast list is incomplete",
        description="Shows the missing-details box whatever the size of the cast.",
    )
    cast_note: PermissiveStr | None = Field(
        default=None,
        title="Custom text for the cast missing-details box",
        description="Only shown with `cast_incomplete`.",
    )
    crew_incomplete: bool = Field(
        default=False,
        title="The crew list is incomplete",
        description=(
            "Shows the missing-details box whatever the size of the crew; it "
            "appears on its own below five crew."
        ),
    )
    crew_note: PermissiveStr | None = Field(
        default=None,
        title="Custom text for the crew missing-details box",
    )
    ignore_missing: bool = Field(
        default=False,
        title="Suppress missing-detail warnings",
        description="Set for shows the archive does not expect to complete.",
    )
    published: bool = Field(
        default=True,
        title="The show is published",
        description=(
            "A flag from the old Jekyll site. Every use sets it true, which was "
            "already the default, so it changes nothing."
        ),
    )
    note: PermissiveStr | None = Field(
        default=None,
        title="A note about the show",
    )
    prod_shots: str | None = Field(
        default=None,
        title="SmugMug album id for production shots",
        description="The first 350 items of the album are fetched.",
    )
    assets: list[Asset] = Field(
        default=[],
        title="Publicity and other materials",
    )
    links: list[Link] = Field(
        default=[],
        title="Reviews, news stories and other links",
    )
    comment: PermissiveStr | None = editor_comment()


class Committee(NthpModel):
    """One year's committee, in `_committees/<YY_YY>.md`."""

    id: str | None = Field(
        default=None,
        title="Year identifier",
        description="Taken from the filename; committees do not author one.",
        examples=["12_13"],
    )
    title: str | None = Field(
        default=None,
        title="Page title",
        description="Formatted `YYYY-YY`.",
        examples=["2012-13"],
    )
    committee: list[PersonRef] = Field(
        title="Committee members",
        description="Each entry needs a `role`, or it appears in no role index.",
    )


class Venue(NthpModel):
    """
    A venue with a record of its own, in `_venues/<venue-name>.md`.

    Most venues are named by shows alone and are published as stubs; a document
    here gives one a description, links and a location.
    """

    id: str | None = Field(
        default=None,
        title="Venue identifier",
        description=(
            "Taken from the filename, which must be the slug of the name the shows use."
        ),
        examples=["nottingham-new-theatre"],
    )
    title: str = Field(
        title="Venue title",
        description=(
            "Must match how shows name the venue, and match the filename slugified."
        ),
    )
    title_short: PermissiveStr | None = Field(
        default=None,
        title="Short form of the venue title",
    )
    links: list[Link] = Field(
        default=[],
        title="Official websites, social media and articles",
    )
    built: int | None = Field(
        default=None,
        title="Year the venue was built",
        examples=[1925],
    )
    images: list[str] = Field(
        default=[],
        title="SmugMug image ids of the venue",
    )
    location: Location | None = Field(
        default=None,
        title="Exact location of the venue",
    )
    city: str | None = Field(
        default=None,
        title="City the venue is in",
        examples=["Nottingham"],
    )
    sort: int | None = Field(
        default=None,
        title="Manual sort order in the venue listing",
    )
    comment: PermissiveStr | None = editor_comment()


class PersonAlias(NthpModel):
    """Another name a person is credited or published under."""

    type: PermissiveStr | None = Field(
        default=None,
        title="What kind of name this is",
        examples=["maiden", "stage"],
    )
    name: str = Field(title="The name", examples=["Freddie Bloggs"])


class Person(NthpModel):
    """
    A person with a record of their own, in `_people/<firstname_lastname>.md`.

    Everyone credited on a show gets a page; a document here adds a biography and
    everything below.
    """

    id: str | None = Field(
        default=None,
        title="Person identifier",
        description=(
            "Taken from the filename. Set it to join a person to credits spelled "
            "another way."
        ),
        examples=["fred_bloggs"],
    )
    title: str = Field(
        title="Person name",
        description="Formatted `Firstname Lastname`, and matching the filename.",
        examples=["Fred Bloggs"],
    )
    pre_nominal: str | None = Field(
        default=None,
        title="Style placed before the name",
        description=(
            "Free text, as it should read. `title` stays the bare name, as the "
            "person id comes from it."
        ),
        examples=["Sir", "Dame", "Professor"],
    )
    post_nominals: list[str] = Field(
        default=[],
        title="Honours and fellowships placed after the name",
        description=(
            "Granted in later life, in the order they should read. Free text, held "
            "to no list. Not for a New Theatre or university award, which is "
            "`award`. `title` stays the bare name, as the person id comes from it."
        ),
        examples=[["OBE", "FRS"]],
    )
    alias: PermissiveStr | None = Field(
        default=None,
        title="Another name this person goes by",
    )
    aliases: list[PersonAlias] = Field(
        default=[],
        title="Other names this person is credited or published under",
    )
    gender: PermissiveStr | None = Field(
        default=None,
        title="Person gender",
        description="No longer used; omit from new records.",
    )
    contact_allowed: bool = Field(
        default=False,
        title="The person agreed to be contacted about the archive",
        description="For the archivists; never published.",
    )
    submitted: FuzzyDate | bool | None = Field(
        default=None,
        title="Date of their last submission",
        description=(
            "`YYYY-MM-DD`. Omitted where the person has made no submission and the "
            "archive collated their record."
        ),
    )
    headshot: str | None = Field(
        default=None,
        title="SmugMug id of the headshot",
    )
    course: list[PermissiveStr] = Field(
        default=[],
        title="Course or courses the person studied",
        description="A bare value is read as a list of one, but a list is the style.",
        examples=[["English"]],
    )
    graduated: int | None = Field(
        default=None,
        title="Year the person graduated",
        description=(
            "`YYYY`. Estimated from their credits where absent, and an award needs "
            "one to appear on a year page."
        ),
        examples=[2013],
    )
    award: PermissiveStr | None = Field(
        default=None,
        title="Award the person received on leaving the theatre",
        description=(
            "Title case. Anything outside Fellowship, Commendation, Merit and "
            "Union Prize appears on their page but on no year page."
        ),
        examples=["Fellowship", "Commendation"],
    )
    careers: list[PermissiveStr] = Field(
        default=[],
        title="Careers, theatre or otherwise",
        description=(
            "Also accepted as `career`. A bare value is read as a list of one, but "
            "a list is the style."
        ),
    )
    links: list[Link] = Field(
        default=[],
        title="Links to external profiles and other sites",
    )
    news: list[Link] = Field(
        default=[],
        title="Links to news stories about the person",
        description="Each should carry a `title`, a `date` and an `href`.",
    )
    comment: PermissiveStr | None = editor_comment()

    @model_validator(mode="before")
    @classmethod
    def accept_career_alias(cls, values: dict) -> dict:
        """Most records use `careers`, a couple use `career`."""
        if isinstance(values, dict) and "career" in values:
            values = dict(values)
            values["careers"] = values.pop("career")
        return values

    @field_validator("course", "careers", mode="before")
    @classmethod
    def coerce_to_list(cls, value: object) -> object:
        """Both fields are authored as either a single value or a list of them."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @field_validator("award", mode="before")
    @classmethod
    def blank_award_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class HistoryRecordImage(NthpModel):
    """An image illustrating a key event."""

    href: str = Field(title="Link to the image")
    alt: str = Field(title="Alt text for the image", description="A short caption.")


class HistoryRecord(NthpModel):
    """One key event in the theatre's history."""

    year: PermissiveStr = Field(
        title="Year, range or approximation the event falls in",
        examples=["2011", "2001-2005", "1980s"],
    )
    academic_year: str | None = Field(
        default=None,
        title="Academic year the event belongs to",
        description="`YY_YY`, which puts the event on that year's page.",
        examples=["12_13"],
    )
    title: str = Field(title="Title of the event")
    description: str = Field(
        title="A bit about the event",
        description="A sentence or a short paragraph. Markdown is supported.",
    )
    image: HistoryRecordImage | None = Field(
        default=None,
        title="An image illustrating the event",
    )

    @field_validator("academic_year")
    @classmethod
    def require_valid_academic_year(cls, value: str | None) -> str | None:
        if value is not None and not years.check_source_year_id_is_valid(value):
            raise ValueError("Invalid academic year")
        return value


class HistoryRecordCollection(BaseCollectionModel[HistoryRecord]):
    pass


class CrewRoleDefinition(NthpModel):
    """
    A crew role as defined by the content repo's `_data/roles.yaml`.

    Icons and the `show` flag are presentation concerns and are ignored.
    """

    role: str = Field(
        title="Canonical name of the role",
        examples=["Lighting Designer"],
    )
    aliases: list[str] = Field(
        default=[],
        title="Other names credits use for this role",
        description="Credits under an alias are indexed under the canonical name.",
    )
    icon: str | None = Field(
        default=None,
        title="Icon class for the site",
        description="A presentation concern; ignored by the API.",
    )
    show: bool = Field(
        default=True,
        title="Show the role on the site",
        description="A presentation concern; ignored by the API.",
    )

    @field_validator("role", "aliases", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        """Names in roles.yaml carry trailing whitespace."""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            return [item.strip() if isinstance(item, str) else item for item in value]
        return value


class CrewRoleDefinitionCollection(BaseCollectionModel[CrewRoleDefinition]):
    pass


class LinkTypeDefinition(NthpModel):
    """
    A link type as defined by the content repo's `_data/link-types.yaml`.

    Icons and proofer flags are presentation concerns and are ignored.
    """

    type: str = Field(
        title="Name of the link type",
        description="Matched against `type` on every link.",
        examples=["facebook", "review"],
    )
    href: str | None = Field(
        default=None,
        title="Template building an href from a link's username",
        description="`{}` is replaced by the link's `username`.",
        examples=["https://www.facebook.com/{}"],
    )
    is_news: bool = Field(
        default=False,
        title="Links of this type are news stories",
    )
    icon: str | None = Field(
        default=None,
        title="Icon class for the site",
        description="A presentation concern; ignored by the API.",
    )
    data: str | None = Field(
        default=None,
        title="Extra data for the site",
        description="A presentation concern; ignored by the API.",
    )

    @field_validator("type", "href", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        """Types in link-types.yaml carry trailing whitespace."""
        if isinstance(value, str):
            return value.strip()
        return value


class LinkTypeDefinitionCollection(BaseCollectionModel[LinkTypeDefinition]):
    pass
