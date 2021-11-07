import json
import logging
import shutil
from pathlib import Path
from typing import List

from nthp_build import database, schema, years
from nthp_build.config import settings

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("dist")


def clean_dist():
    try:
        shutil.rmtree(OUTPUT_DIR)
    except FileNotFoundError:
        pass


def make_out_path(directory: Path, file: str) -> Path:
    path = OUTPUT_DIR / directory / Path(file + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def dump_show(inst: database.Show) -> Path:
    show = schema.ShowDetail(**json.loads(inst.data))
    path = make_out_path(Path("shows"), show.id)
    with open(path, "w") as f:
        f.write(show.json(by_alias=True))
    return path


def dump_year(year: int) -> schema.YearDetail:
    year_id = years.get_year_id(year)
    path = make_out_path(Path("years"), year_id)
    shows = database.Show.select().where(database.Show.year_id == year_id)
    committee = database.PersonRole.select().where(
        database.PersonRole.target_type == database.PersonRoleType.COMMITTEE,
        database.PersonRole.target_id == year_id,
    )
    year_detail = schema.YearDetail(
        title=f"{year}–{str(year+1)[-2:]}",
        decade=int(str(year)[-2:]),
        year_id=year_id,
        start_year=year,
        grad_year=year + 1,
        show_count=len(shows),
        shows=[json.loads(show_inst.data) for show_inst in shows],
        committee=[
            schema.PersonRoleList(**json.loads(person_inst.data))
            for person_inst in committee
        ],
        fellows=[],
        commendations=[],
    )
    with open(path, "w") as f:
        f.write(year_detail.json(by_alias=True))
    return year_detail


def dump_year_index(year_details: List[schema.YearDetail]):
    path = make_out_path(Path("years"), "index")
    year_collection = schema.YearListCollection(
        [schema.YearList(**year_detail.dict()) for year_detail in year_details]
    )
    with open(path, "w") as f:
        f.write(year_collection.json(by_alias=True))


def dump_all():
    log.info("Dumping shows")
    for show_inst in database.Show.select():
        dump_show(show_inst)

    log.info("Dumping years")
    years_detail = [
        dump_year(year) for year in range(settings.year_start, settings.year_end)
    ]

    log.info("Dumping year index")
    dump_year_index(years_detail)
