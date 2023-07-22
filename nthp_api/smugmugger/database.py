import logging

import peewee

from nthp_api.smugmugger.config import settings

log = logging.getLogger(__name__)

db = peewee.SqliteDatabase(settings.smugmug_db_uri)


class SmugMuggerDbModel(peewee.Model):
    class Meta:
        database = db


class SmugMugResponse(SmugMuggerDbModel):
    id = peewee.CharField(primary_key=True)
    last_updated = peewee.DateTimeField()
    last_fetched = peewee.DateTimeField()
    data = peewee.TextField()


MODELS = [SmugMugResponse]


def init_db(create: bool = False):
    log.info(f"Initializing database: {db.database}")

    db.connect()
    if create:
        db.drop_tables(MODELS)
    db.create_tables(MODELS)
