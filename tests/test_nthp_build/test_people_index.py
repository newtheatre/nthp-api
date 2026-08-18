import json
from pathlib import Path

import freezegun
import pytest

from nthp_api.nthp_build import database, dumper, models, people
from nthp_api.nthp_build.parallel import DumperSharedState

FRED = "fred_bloggs"
ALICE = "alice_froggs"

THE_TEMPEST = "99_00/the_tempest"
TITUS_ANDRONICUS = "99_00/titus_andronicus"


def make_show(show_id: str, title: str) -> database.Show:
    return database.Show.create(
        id=show_id,
        source_path=f"_shows/{show_id}.md",
        year=1999,
        year_id="99_00",
        title=title,
        assets="[]",
        data="{}",
    )


def make_real_person(person_id: str, person: models.Person) -> database.Person:
    return database.Person.create(
        id=person_id,
        title=person.title,
        graduated=person.graduated,
        headshot=person.headshot,
        data=person.model_dump_json(),
        content="<p>A bio</p>",
    )


def save_role(person_name: str, target: str, target_type: str, role: str) -> None:
    people.save_person_roles(
        target=target,
        target_type=target_type,
        target_year=1999,
        person_list=[models.PersonRef(name=person_name, role=role)],
    )


@pytest.fixture()
def populated_db(test_db):
    """Fred has a bio, two roles in one show and two committee terms; Alice does not."""
    make_show(THE_TEMPEST, "The Tempest")
    make_show(TITUS_ANDRONICUS, "Titus Andronicus")
    make_real_person(
        FRED,
        models.Person(
            id=FRED,
            title="Fred Bloggs",
            submitted="2016-05",
            headshot="abc123",
            graduated=2016,
        ),
    )
    save_role("Fred Bloggs", THE_TEMPEST, database.PersonRoleType.CAST, "Prospero")
    save_role("Fred Bloggs", THE_TEMPEST, database.PersonRoleType.CREW, "Director")
    save_role("Fred Bloggs", "99_00", database.PersonRoleType.COMMITTEE, "President")
    save_role("Fred Bloggs", "00_01", database.PersonRoleType.COMMITTEE, "President")
    save_role("Alice Froggs", TITUS_ANDRONICUS, database.PersonRoleType.CAST, "Titus")
    return test_db


@pytest.fixture()
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(dumper, "OUTPUT_DIR", tmp_path)
    return tmp_path


def dump_index(output_dir: Path) -> list[dict]:
    dumper.dump_people_index(state=DumperSharedState(search_documents=[]))
    return json.loads((output_dir / "people" / "index.json").read_text())


def get_entry(entries: list[dict], person_id: str) -> dict:
    return next(entry for entry in entries if entry["id"] == person_id)


class TestRoleCounts:
    def test_show_roles_count_distinct_shows(self, populated_db):
        """Two roles in one show is one show, as the detail page groups them."""
        assert people.get_show_role_counts() == {FRED: 1, ALICE: 1}

    def test_committee_roles_count_each_term(self, populated_db):
        assert people.get_committee_role_counts() == {FRED: 2}

    @pytest.mark.parametrize("person_id", [FRED, ALICE])
    def test_counts_match_detail_page(self, populated_db, person_id):
        detail = people.make_person_detail(models.Person(id=person_id, title="Whoever"))
        assert people.get_show_role_counts().get(person_id, 0) == len(detail.show_roles)
        assert people.get_committee_role_counts().get(person_id, 0) == len(
            detail.committee_roles
        )


@freezegun.freeze_time("2026-08-18")
class TestDumpPeopleIndex:
    def test_real_person_entry(self, populated_db, output_dir):
        entry = get_entry(dump_index(output_dir), FRED)
        assert entry == {
            "id": FRED,
            "title": "Fred Bloggs",
            "submitted": "2016-05",
            "headshot": "abc123",
            "graduated": {
                "yearTitle": "2016",
                "yearDecade": 201,
                "yearId": "15_16",
                "estimated": False,
            },
            "showRoleCount": 1,
            "committeeRoleCount": 2,
            "hasBio": True,
        }

    def test_virtual_person_entry(self, populated_db, output_dir):
        entry = get_entry(dump_index(output_dir), ALICE)
        assert entry["hasBio"] is False
        assert entry["showRoleCount"] == 1
        assert entry["committeeRoleCount"] == 0
        assert "headshot" not in entry

    def test_sorted_by_id(self, populated_db, output_dir):
        entries = dump_index(output_dir)
        assert [entry["id"] for entry in entries] == sorted(
            entry["id"] for entry in entries
        )

    def test_entries_match_detail_pages(self, populated_db, output_dir):
        state = DumperSharedState(search_documents=[])
        dumper.dump_real_people(state=state)
        dumper.dump_virtual_people(state=state)
        entry_ids = {entry["id"] for entry in dump_index(output_dir)}
        detail_ids = {
            path.stem
            for path in (output_dir / "people").glob("*.json")
            if path.stem != "index"
        }
        assert entry_ids == detail_ids
