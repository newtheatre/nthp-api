import peewee

from nthp_build import database


def get_show_query() -> peewee.Query:
    return database.Show.select().order_by(
        # Sort by season_sort then date_start. Means we can opt to ignore season_sort
        # within a year. However if you start using season_sort it should be added to
        # all shows.
        database.Show.season_sort,
        database.Show.date_start,
    )
