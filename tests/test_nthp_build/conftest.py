import pytest
from playhouse.sqlite_ext import SqliteExtDatabase

from nthp_api.nthp_build.database import MODELS


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
