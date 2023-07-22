import json
from collections.abc import Iterable

from peewee import ModelSelect
from slugify import slugify

from nthp_api.nthp_build import database, models
from nthp_api.nthp_build.schema import Location, VenueCollection, VenueDetail, VenueList
from nthp_api.nthp_build.shows import get_show_list_item


def get_venue_id(name: str) -> str:
    return slugify(name.replace("'", ""), separator="-")


ShowVenueMap = dict[str, list[database.Show]]


def get_show_venue_map(venue_query: ModelSelect) -> ShowVenueMap:
    """
    Returns a map of venue IDs to a list of shows for that venue.
    """
    shows_per_venue_query = database.Show.select().where(
        database.Show.venue_id << venue_query.select(database.Venue.id)
    )
    return {
        venue.id: [show for show in shows_per_venue_query if show.venue_id == venue.id]
        for venue in venue_query
    }


def get_venue_collection(
    venue_query: Iterable[database.Venue], show_venue_map: ShowVenueMap
) -> VenueCollection:
    return VenueCollection(
        [
            VenueList(
                id=venue_inst.id,
                name=venue_inst.name,
                show_count=len(show_venue_map[venue_inst.id]),
                built=venue_model.built,
                location=Location.from_model(venue_model.location)
                if venue_model.location
                else None,
                city=venue_model.city,
            )
            for venue_inst, venue_model in (
                (v, models.Venue(**json.loads(v.data))) for v in venue_query
            )
        ]
    )


def get_venue_detail(
    venue_inst: database.Venue, shows: list[database.Show]
) -> VenueDetail:
    venue_data = models.Venue(**json.loads(venue_inst.data))
    return VenueDetail(
        id=venue_inst.id,
        name=venue_inst.name,
        show_count=len(shows),
        built=venue_data.built,
        location=Location.from_model(venue_data.location)
        if venue_data.location
        else None,
        city=venue_data.city,
        shows=[get_show_list_item(show) for show in shows],
        content=venue_inst.content,
    )
