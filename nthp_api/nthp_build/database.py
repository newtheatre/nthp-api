import logging

import peewee

from nthp_api.nthp_build.config import settings

log = logging.getLogger(__name__)
db = peewee.SqliteDatabase(settings.db_uri)


class NthpDbModel(peewee.Model):
    class Meta:
        database = db


class DbCompatEnumMixin:
    def __str__(self):
        return self.value


class TargetType:
    SHOW = "show"


class PersonRoleType:
    CAST = "CAST"
    CREW = "CREW"
    COMMITTEE = "COMMITTEE"


class PersonRole(NthpDbModel):
    target_id = peewee.CharField(index=True)
    target_type = peewee.CharField(index=True)
    # Uses YYYY, not YY_YY, 2000 means 2000-2001
    target_year = peewee.IntegerField(index=True)

    person_id = peewee.CharField(index=True, null=True)
    person_name = peewee.CharField(null=True)
    role = peewee.CharField(null=True, index=True)
    is_person = peewee.BooleanField(index=True)
    data = peewee.TextField()


class Show(NthpDbModel):
    id = peewee.CharField(primary_key=True)
    source_path = peewee.CharField()
    year = peewee.IntegerField()
    year_id = peewee.CharField(index=True)
    title = peewee.CharField()
    venue_id = peewee.CharField(index=True, null=True)
    season_sort = peewee.IntegerField(null=True, index=True)
    date_start = peewee.DateField(null=True, index=True)
    date_end = peewee.DateField(null=True)
    primary_image = peewee.CharField(null=True)
    assets = peewee.TextField()
    data = peewee.TextField()
    content = peewee.TextField(null=True)
    plaintext = peewee.TextField(null=True)


class PlaywrightShow(NthpDbModel):
    play_id = peewee.CharField(index=True)
    play_name = peewee.CharField()
    playwright_id = peewee.CharField(index=True)
    playwright_name = peewee.CharField()
    show_id = peewee.CharField(index=True)
    person_id = peewee.CharField(null=True, index=True)


class Venue(NthpDbModel):
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField()
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


class Trivia(NthpDbModel):
    target_id = peewee.CharField(index=True)
    target_type = peewee.CharField(index=True)
    target_name = peewee.CharField()
    target_image_id = peewee.CharField(null=True)
    # Uses YYYY, not YY_YY, 2000 means 2000-2001
    target_year = peewee.IntegerField(index=True, null=True)

    person_id = peewee.CharField(index=True, null=True)
    person_name = peewee.CharField(null=True)

    quote = peewee.TextField()
    submitted = peewee.DateField(null=True, index=True)

    data = peewee.TextField()


class HistoryRecord(NthpDbModel):
    year = peewee.CharField()
    academic_year = peewee.CharField(null=True, index=True)
    title = peewee.CharField()
    description = peewee.TextField()


class Asset(NthpDbModel):
    target_id = peewee.CharField(index=True)
    target_type = peewee.CharField(index=True)

    asset_source = peewee.CharField(index=True)
    asset_type = peewee.CharField(index=True)
    asset_mime_type = peewee.CharField(null=True)
    asset_id = peewee.CharField(index=True)

    asset_category = peewee.CharField(null=True)
    asset_title = peewee.CharField(null=True)
    asset_page = peewee.IntegerField(null=True)

    asset_smugmug_data = peewee.CharField(null=True)


MODELS = [Show, PlaywrightShow, Venue, PersonRole, Person, Trivia, HistoryRecord, Asset]


def init_db(create: bool = False):
    log.info(f"Initializing database: {db.database}")

    db.connect()
    if create:
        db.drop_tables(MODELS)
    db.create_tables(MODELS)


def show_stats():
    for model in MODELS:
        log.info(f"{model.__name__} has {model.select().count()} records")
