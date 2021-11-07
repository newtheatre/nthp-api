import peewee

db = peewee.SqliteDatabase("nthp.db")


def init_db(create: bool = False):
    MODELS = [PersonRole, Show, Venue]
    db.connect()
    if create:
        db.drop_tables(MODELS)
        db.create_tables(MODELS)


class NTDB(peewee.Model):
    class Meta:
        database = db


class PersonRoleType:
    CAST = "CAST"
    CREW = "CREW"
    COMMITTEE = "COMMITTEE"


class PersonRole(NTDB):
    target_id = peewee.CharField(index=True)
    target_type = peewee.CharField(index=True)

    person_id = peewee.CharField(index=True, null=True)
    person_name = peewee.CharField(null=True)
    role = peewee.CharField(null=True, index=True)
    is_person = peewee.BooleanField(index=True)
    data = peewee.TextField()


class Show(NTDB):
    id = peewee.CharField(primary_key=True)
    year_id = peewee.CharField(index=True)
    title = peewee.CharField()
    source_path = peewee.CharField()
    data = peewee.TextField()
    content = peewee.TextField(null=True)


class Venue(NTDB):
    id = peewee.CharField(primary_key=True)
    title = peewee.CharField()
    data = peewee.TextField()
