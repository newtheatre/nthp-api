import pytest
from peewee import SqliteDatabase

from nthp_api.nthp_build import assets, links
from nthp_api.nthp_build.database import MODELS


@pytest.fixture()
def test_db():
    links.get_link_type_definitions.cache_clear()
    assets.clear_image_info_caches()
    test_db = SqliteDatabase(":memory:")
    with test_db.bind_ctx(MODELS):
        test_db.create_tables(MODELS)
        try:
            yield test_db
        finally:
            test_db.drop_tables(MODELS)
            test_db.close()
