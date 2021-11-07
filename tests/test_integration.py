import pytest

from nthp_build import database, dumper, loader


def test_load():
    database.init_db(create=True)
    loader.run_loaders()


@pytest.mark.depends(on=["test_load"])
def test_dump():
    dumper.delete_output_dir()
    dumper.dump_all()
