import json
import logging
from collections import Counter, defaultdict
from typing import NamedTuple

from slugify import slugify

from nthp_api.nthp_build import assets, database, models
from nthp_api.nthp_build.schema import Location, VenueDetail, VenueList
from nthp_api.nthp_build.shows import get_show_list_item

log = logging.getLogger(__name__)

SENTINEL_VENUE_NAMES = {
    "unknown": "Venue unknown",
    "youtube": "Online — YouTube",
}


def get_venue_id(name: str) -> str:
    return slugify(name.replace("'", ""), separator="-")


class VenueRecord(NamedTuple):
    """
    A venue to output, whether or not the content repo files a document for it.

    Shows reference venues by an id slugified from the authored `venue:` string, so
    most venues have no document of their own; those become stubs.
    """

    id: str
    name: str
    sentinel: bool
    venue_sort: str | None
    document: database.Venue | None
    document_data: models.Venue | None
    shows: list[database.Show]

    @property
    def has_record(self) -> bool:
        return self.document is not None


def get_venue_shows() -> dict[str, list[database.Show]]:
    """Shows of each referenced venue, in date order; venues span academic years."""
    venue_shows: dict[str, list[database.Show]] = defaultdict(list)
    for show in (
        database.Show.select()
        .where(database.Show.venue_id.is_null(False))  # type: ignore[attr-defined]
        .order_by(database.Show.date_start, database.Show.id)
    ):
        venue_shows[show.venue_id].append(show)
    return venue_shows


def get_most_common(values: Counter[str]) -> str | None:
    """Most common value, ties broken alphabetically to keep output stable."""
    if not values:
        return None
    return min(values, key=lambda value: (-values[value], value))


def get_stub_name(venue_id: str, shows: list[database.Show]) -> str:
    spellings = Counter(show.venue_name for show in shows if show.venue_name)
    if len(spellings) > 1:
        log.warning(
            f"Venue {venue_id} is authored as {sorted(spellings)}, "
            f"using the most common spelling"
        )
    return get_most_common(spellings) or venue_id


def get_venue_sort(shows: list[database.Show]) -> str | None:
    return get_most_common(
        Counter(show.venue_sort for show in shows if show.venue_sort)
    )


def make_venue_record(
    venue_id: str, document: database.Venue | None, shows: list[database.Show]
) -> VenueRecord:
    document_data = (
        models.Venue(**json.loads(document.data)) if document is not None else None
    )
    if venue_id in SENTINEL_VENUE_NAMES:
        name = SENTINEL_VENUE_NAMES[venue_id]
    elif document is not None:
        name = document.name
    else:
        name = get_stub_name(venue_id, shows)
    return VenueRecord(
        id=venue_id,
        name=name,
        sentinel=venue_id in SENTINEL_VENUE_NAMES,
        venue_sort=get_venue_sort(shows),
        document=document,
        document_data=document_data,
        shows=shows,
    )


def get_venue_records() -> list[VenueRecord]:
    """Every venue filed as a document or referenced by a show, by id."""
    venue_shows = get_venue_shows()
    documents = {venue.id: venue for venue in database.Venue.select()}
    return [
        make_venue_record(
            venue_id, documents.get(venue_id), venue_shows.get(venue_id, [])
        )
        for venue_id in sorted(set(documents) | set(venue_shows))
    ]


def get_venue_list(record: VenueRecord) -> VenueList:
    data = record.document_data
    return VenueList(
        id=record.id,
        name=record.name,
        show_count=len(record.shows),
        venue_sort=record.venue_sort,
        has_record=record.has_record,
        sentinel=record.sentinel,
        built=data.built if data else None,
        location=(
            Location.from_model(data.location) if data and data.location else None
        ),
        city=data.city if data else None,
    )


def get_venue_detail(record: VenueRecord) -> VenueDetail:
    data = record.document_data
    return VenueDetail(
        **get_venue_list(record).model_dump(),
        assets=(
            [
                assets.add_smugmug_image_info(asset)
                for asset in assets.assets_from_venue_model(data)
            ]
            if data
            else []
        ),
        shows=[get_show_list_item(show) for show in record.shows],
        content=record.document.content if record.document else None,
    )
