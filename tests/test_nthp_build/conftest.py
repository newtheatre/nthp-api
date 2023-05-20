import pytest
from nthp_build.database import MODELS
from playhouse.sqlite_ext import SqliteExtDatabase


@pytest.fixture()
def test_db():
    test_db = SqliteExtDatabase(":memory:")
    with test_db.bind_ctx(MODELS):
        test_db.create_tables(MODELS)
        try:
            yield test_db
        finally:
            test_db.drop_tables(MODELS)
            test_db.close()
