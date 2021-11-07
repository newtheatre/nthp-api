import logging

import peewee

log = logging.getLogger(__name__)
db = peewee.SqliteDatabase("nthp.db")


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
    year_id = peewee.CharField(index=True)
    title = peewee.CharField()
    source_path = peewee.CharField()
    data = peewee.TextField()
    content = peewee.TextField(null=True)


class Venue(NthpDbModel):
    id = peewee.CharField(primary_key=True)
    title = peewee.CharField()
    data = peewee.TextField()


class Person(NthpDbModel):
    id = peewee.CharField(primary_key=True)
    title = peewee.CharField()
    graduated = peewee.IntegerField(index=True, null=True)
    data = peewee.TextField()
    content = peewee.TextField(null=True)


MODELS = [Show, Venue, PersonRole, Person]


def init_db(create: bool = False):
    db.connect()
    if create:
        db.drop_tables(MODELS)
        db.create_tables(MODELS)


def show_stats():
    for model in MODELS:
        log.info(f"{model.__name__} has {model.select().count()} records")
