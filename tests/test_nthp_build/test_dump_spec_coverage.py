"""Every file a dump writes must be a file the spec documents."""

import json
import re
from pathlib import Path

import pytest

from nthp_api.nthp_build import assets, database, dumper, models, people, spec
from nthp_api.nthp_build.assets import AssetSource, AssetType
from nthp_api.nthp_build.parallel import DumperSharedState
from nthp_api.smugmugger import SmugMugImage

# Files written deliberately outside the API spec. Shrink this as they gain
# spec entries; a dump output missing from the spec by accident must fail here.
UNDOCUMENTED_PATHS = {
    "openapi.json",  # the spec itself, which cannot document itself
}
UNDOCUMENTED_DIRECTORIES = {
    "content-schema",  # the shape of the content repo, not of the API
}

YEAR_ID = "1999-00"
SHOW_ID = f"{YEAR_ID}/the_tempest"
PERSON_ID = "fred_bloggs"
ALBUM_ID = "W38sb3"


def make_path_pattern(spec_path: str) -> re.Pattern[str]:
    """A spec path as a regex, its `{param}` segments matching one path segment."""
    parts = re.split(r"\{[^}]+\}", spec_path.removeprefix("/"))
    return re.compile("[^/]+".join(re.escape(part) for part in parts) + "$")


SPEC_PATH_PATTERNS = [make_path_pattern(path) for path in spec.SPEC["paths"]]


def is_documented(written_path: str) -> bool:
    return any(pattern.match(written_path) for pattern in SPEC_PATH_PATTERNS)


@pytest.fixture()
def populated_db(test_db):
    """One of everything a dumper walks, so every parameterised path is written."""
    database.Show.create(
        id=SHOW_ID,
        source_path=f"_shows/{SHOW_ID}.md",
        year=1999,
        year_id=YEAR_ID,
        title="The Tempest",
        venue_id="new_theatre",
        venue_name="New Theatre",
        season_id="in_house",
        date_start="1999-11-13",
        date_end="1999-11-17",
        primary_image="abc123",
        assets="[]",
        data=models.Show(
            id=SHOW_ID, title="The Tempest", season="In House"
        ).model_dump_json(),
    )
    database.Venue.create(
        id="new_theatre",
        source_path="_venues/new_theatre.md",
        name="New Theatre",
        data=models.Venue(id="new_theatre", title="New Theatre").model_dump_json(),
    )
    database.Person.create(
        id=PERSON_ID,
        title="Fred Bloggs",
        graduated=2000,
        headshot="def456",
        data=models.Person(
            id=PERSON_ID, title="Fred Bloggs", graduated=2000
        ).model_dump_json(),
        content="<p>A bio</p>",
    )
    database.PlaywrightShow.create(
        play_id="the_tempest",
        play_name="The Tempest",
        playwright_id="william_shakespeare",
        playwright_name="William Shakespeare",
        show_id=SHOW_ID,
    )
    database.HistoryRecord.create(
        year="1999",
        academic_year="99_00",
        title="Something happened",
        description="It really did.",
    )
    database.CrewRoleDefinition.create(name="Director", sort=0, aliases="[]")
    for target, target_type, role in (
        (SHOW_ID, database.PersonRoleType.CAST, "Prospero"),
        (SHOW_ID, database.PersonRoleType.CREW, "Director"),
        (YEAR_ID, database.PersonRoleType.COMMITTEE, "President"),
    ):
        people.save_person_roles(
            target=target,
            target_type=target_type,
            target_year=1999,
            person_list=[models.PersonRef(name="Fred Bloggs", role=role)],
        )
    album = assets.save_asset(
        target_id=SHOW_ID,
        target_type=assets.AssetTarget.SHOW,
        source=AssetSource.SMUGMUG,
        type=AssetType.ALBUM,
        id=ALBUM_ID,
    )
    album.asset_smugmug_data = json.dumps(
        [
            SmugMugImage(
                Uri=f"/api/v2/album/{ALBUM_ID}/image/Dg7GGwL-0",
                Date="2013-06-04T12:00:00+00:00",
                FileName="tempest.jpg",
                Format="JPG",
                ImageKey="Dg7GGwL",
                IsVideo=False,
                OriginalHeight=1600,
                OriginalWidth=1200,
                Processing=False,
                ThumbnailUrl="https://photos.smugmug.com/photos/i-Dg7GGwL/0/Th/x.jpg",
                Title="",
                WebUri="https://photos.newtheatre.org.uk/i-Dg7GGwL",
            ).model_dump(mode="json", by_alias=True)
        ]
    )
    album.save()
    return test_db


@pytest.fixture()
def dumped(populated_db, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> set[str]:
    """Run every dumper in series, returning what it wrote, relative to the root."""
    monkeypatch.setattr(dumper, "OUTPUT_DIR", tmp_path)
    state = DumperSharedState(search_documents=[])
    for dump in [*dumper.DUMPERS, *dumper.POST_DUMPERS]:
        dump.dumper(state=state)
    return {
        str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*.json")
    } - UNDOCUMENTED_PATHS


class TestDumpMatchesSpec:
    def test_the_dump_writes_the_paths_under_test(self, dumped: set[str]):
        """A dump that wrote nothing interesting would pass the coverage test."""
        assert {
            "shows/1999-00/the_tempest.json",
            "people/fred_bloggs.json",
            "venues/new_theatre.json",
            "collaborators/fred_bloggs.json",
            f"assets/album/{ALBUM_ID}.json",
            "on-this-day/11-13.json",
        } <= dumped

    def test_every_written_file_is_documented(self, dumped: set[str]):
        undocumented = {
            path
            for path in dumped
            if path.split("/")[0] not in UNDOCUMENTED_DIRECTORIES
            and not is_documented(path)
        }
        assert undocumented == set()
