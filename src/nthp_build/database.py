import logging

import peewee

from nthp_build.config import settings

log = logging.getLogger(__name__)
db = peewee.SqliteDatabase(settings.db_uri)


class NthpDbModel(peewee.Model):
    class Meta:
        database = db


class PersonRoleType:
    CAST = "CAST"
    CREW = "CREW"
    COMMITTEE = "COMMITTEE"


class PersonRole(NthpDbModel):
    target_id = peewee.CharField(index=True)
    target_type = peewee.CharField(index=True)

    person_id = peewee.CharField(index=True, null=True)
    person_name = peewee.CharField(null=True)
    role = peewee.CharField(null=True, index=True)
    is_person = peewee.BooleanField(index=True)
    data = peewee.TextField()


class Show(NthpDbModel):
    id = peewee.CharField(primary_key=True)
    source_path = peewee.CharField()
    year_id = peewee.CharField(index=True)
    title = peewee.CharField()
    season_sort = peewee.IntegerField(null=True, index=True)
    date_start = peewee.DateField(null=True, index=True)
    date_end = peewee.DateField(null=True)
    primary_image = peewee.CharField(null=True)
    data = peewee.TextField()
    content = peewee.TextField(null=True)
    plaintext = peewee.TextField(null=True)


class PlaywrightShow(NthpDbModel):
    playwright_id = peewee.CharField(index=True)
    playwright_name = peewee.CharField()
    show_id = peewee.CharField(index=True)


class Venue(NthpDbModel):
    id = peewee.CharField(primary_key=True)
    title = peewee.CharField()
    data = peewee.TextField()
    content = peewee.TextField(null=True)
    plaintext = peewee.TextField(null=True)


class Person(NthpDbModel):
    id = peewee.CharField(primary_key=True)
    title = peewee.CharField()
    graduated = peewee.IntegerField(index=True, null=True)
    headshot = peewee.CharField(null=True)
    data = peewee.TextField()
    content = peewee.TextField(null=True)
    plaintext = peewee.TextField(null=True)


MODELS = [Show, PlaywrightShow, Venue, PersonRole, Person]


def init_db(create: bool = False):
    log.info(f"Initializing database: {db.database}")

    db.connect()
    if create:
        db.drop_tables(MODELS)
        db.create_tables(MODELS)


def show_stats():
    for model in MODELS:
        log.info(f"{model.__name__} has {model.select().count()} records")
