import json
from pathlib import Path

import pytest

from nthp_api.nthp_build import (
    database,
    dumper,
    models,
    roles,
    schema,
    spec,
    validate,
)
from nthp_api.nthp_build.config import settings
from nthp_api.nthp_build.loader import (
    DataLoaderFunc,
    Loader,
    load_crew_role_definitions,
    run_data_loader,
)
from nthp_api.nthp_build.parallel import DumperSharedState

ROLES_YAML = """
- role: Playwright\x20
  icon: fa fa-pencil\x20
  aliases:\x20
    - Author\x20
    - Writer
- role: Director
  icon: ion-film-marker
  aliases:
    - Co-director
- role: Stage Manager
  icon: fa fa-bookmark
- role: President
  icon: fa fa-star
  show: false
"""


@pytest.fixture()
def _bound_db(test_db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(database, "db", test_db)
    return test_db


@pytest.fixture()
def crew_role_definitions(
    test_db, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _bound_db
) -> list[roles.RoleDefinition]:
    monkeypatch.setattr(settings, "content_root", tmp_path)
    data_dir = tmp_path / "_data"
    data_dir.mkdir()
    (data_dir / "roles.yaml").write_text(ROLES_YAML)
    run_data_loader(
        Loader(
            type=DataLoaderFunc,
            path=Path("_data/roles.yaml"),
            schema_type=models.CrewRoleDefinitionCollection,
            func=load_crew_role_definitions,
        )
    )
    return roles.get_crew_role_definitions()


class TestCrewRoleDefinitionModel:
    def test_strips_trailing_whitespace(self):
        definition = models.CrewRoleDefinition(
            role="Playwright ", aliases=["Author ", "Writer"]
        )
        assert definition.role == "Playwright"
        assert definition.aliases == ["Author", "Writer"]

    def test_ignores_presentation_fields(self):
        definition = models.CrewRoleDefinition(
            role="Director", icon="ion-film-marker", show=False
        )
        assert definition.aliases == []


class TestLoadCrewRoleDefinitions:
    def test_loads_every_role_in_definition_order(self, crew_role_definitions):
        assert [definition.name for definition in crew_role_definitions] == [
            "Playwright",
            "Director",
            "Stage Manager",
            "President",
        ]

    def test_loads_aliases_stripped(self, crew_role_definitions):
        assert crew_role_definitions[0].aliases == {"Author", "Writer"}
        assert crew_role_definitions[2].aliases == set()


class TestCrewRoleCanonicalNames:
    def test_maps_names_and_aliases_to_the_canonical_name(self, crew_role_definitions):
        assert roles.get_crew_role_canonical_names() == {
            "Playwright": "Playwright",
            "Author": "Playwright",
            "Writer": "Playwright",
            "Director": "Director",
            "Co-director": "Director",
            "Stage Manager": "Stage Manager",
            "President": "President",
        }


def make_person_role(
    person_id: str, role: str, target_type: str, target_year: int = 1999
) -> database.PersonRole:
    return database.PersonRole.create(
        target_id="1999-00/a_show"
        if target_type == database.PersonRoleType.CREW
        else "1999-00",
        target_type=target_type,
        target_year=target_year,
        person_id=person_id,
        person_name=person_id.replace("_", " ").title(),
        role=role,
        is_person=True,
        data="{}",
    )


@pytest.fixture()
def populated_db(crew_role_definitions, test_db):
    make_person_role("alice", "Playwright", database.PersonRoleType.CREW)
    make_person_role("bob", "Author", database.PersonRoleType.CREW)
    make_person_role("bob", "Writer", database.PersonRoleType.CREW)
    make_person_role("carol", "Bagpiper", database.PersonRoleType.CREW)

    make_person_role("alice", "President", database.PersonRoleType.COMMITTEE)
    make_person_role("bob", "President", database.PersonRoleType.COMMITTEE, 2000)
    make_person_role(
        "carol", "Marketing Co-ordinator", database.PersonRoleType.COMMITTEE
    )
    make_person_role("dave", "Committee Members", database.PersonRoleType.COMMITTEE)
    make_person_role("erin", "unknown", database.PersonRoleType.COMMITTEE)
    make_person_role("frank", "Unknown", database.PersonRoleType.COMMITTEE)
    return test_db


@pytest.fixture()
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    output_dir = tmp_path / "dist"
    monkeypatch.setattr(dumper, "OUTPUT_DIR", output_dir)
    return output_dir


def dump_roles(output_dir: Path) -> Path:
    dumper.dump_roles(state=DumperSharedState(search_documents=[]))
    return output_dir / "roles"


def read_json(path: Path):
    return json.loads(path.read_text())


class TestCommitteeRoleDefinitions:
    def test_roles_come_from_the_content(self, populated_db):
        names = {
            definition.name for definition in roles.get_committee_role_definitions()
        }
        assert names == {
            "President",
            "Marketing Coordinator",
            "Committee Member",
        }

    def test_unknown_roles_are_excluded(self, populated_db):
        names = {
            definition.name for definition in roles.get_committee_role_definitions()
        }
        assert "unknown" not in names
        assert "Unknown" not in names

    def test_aliases_fold_into_the_canonical_role(self, populated_db):
        definition = next(
            definition
            for definition in roles.get_committee_role_definitions()
            if definition.name == "Committee Member"
        )
        assert definition.aliases == {"Committee Members"}
        people = roles.get_people_committee_roles_by_role(definition)
        assert [holding.person.id for holding in people] == ["dave"]

    def test_every_alias_folds_into_a_known_canonical_name(self):
        canonical_names = set(roles.COMMITTEE_ROLE_ALIASES)
        aliases = set(roles.COMMITTEE_ROLE_CANONICAL_NAMES)
        assert not canonical_names & aliases

    def test_every_role_id_is_unique(self, populated_db):
        role_ids = [
            roles.get_role_id(definition.name)
            for definition in roles.get_committee_role_definitions()
        ]
        assert len(role_ids) == len(set(role_ids))


class TestCrewRoles:
    def test_aliases_fold_into_the_canonical_role(self, populated_db):
        definition = roles.get_crew_role_definitions()[0]
        people = roles.get_people_crew_roles_by_role(definition)
        assert [(holding.person.id, holding.show_count) for holding in people] == [
            ("alice", 1),
            ("bob", 2),
        ]
        assert {holding.role for holding in people} == {"Playwright"}

    def test_count_is_holdings_not_people(self, populated_db):
        expected_holdings = 3
        definition = roles.get_crew_role_definitions()[0]
        assert (
            roles.get_role_holding_count(definition, database.PersonRoleType.CREW)
            == expected_holdings
        )

    def test_roles_without_definition_are_reported(self, populated_db):
        assert roles.get_crew_roles_without_definition() == ["Bagpiper"]

    def test_roles_without_definition_are_reported_by_lint(self, populated_db):
        """Expected and long-tail, so `nthp lint` reports it, not the build."""
        findings = validate.check_crew_role_definitions()
        assert len(findings) == 1
        assert findings[0].value == "Bagpiper"


class TestPersonRefs:
    """The people a role index lists carry their bio and headshot."""

    @staticmethod
    def make_real_person(person_id: str, headshot: str | None = None) -> None:
        database.Person.create(
            id=person_id,
            title=person_id.replace("_", " ").title(),
            headshot=headshot,
            data="{}",
        )

    def test_crew_role_holder_with_a_bio(self, populated_db):
        self.make_real_person("alice", headshot="abc123")
        definition = roles.get_crew_role_definitions()[0]
        [alice, _bob] = roles.get_people_crew_roles_by_role(definition)
        assert alice.person.has_bio is True
        assert alice.person.headshot == schema.ImageRef(id="abc123")

    def test_crew_role_holder_without_a_bio(self, populated_db):
        definition = roles.get_crew_role_definitions()[0]
        [alice, _bob] = roles.get_people_crew_roles_by_role(definition)
        assert alice.person.has_bio is False
        assert alice.person.headshot is None

    def test_cast_member_with_a_bio(self, populated_db):
        self.make_real_person("alice")
        make_person_role("alice", "Prospero", database.PersonRoleType.CAST)
        [alice] = roles.get_people_cast()
        assert alice.person.has_bio is True

    def test_committee_role_holder_with_a_bio(self, populated_db):
        self.make_real_person("alice", headshot="abc123")
        definition = roles.RoleDefinition(name="President")
        holdings = roles.get_people_committee_roles_by_role(definition)
        alice = next(holding for holding in holdings if holding.person.id == "alice")
        assert alice.person.has_bio is True
        assert alice.person.headshot == schema.ImageRef(id="abc123")


class TestDumpRoles:
    def test_crew_index_lists_every_definition_with_counts(
        self, populated_db, output_dir: Path
    ):
        index = read_json(dump_roles(output_dir) / "crew" / "index.json")
        assert [(role["name"], role["holdingCount"]) for role in index] == [
            ("Playwright", 3),
            ("Director", 0),
            ("Stage Manager", 0),
            ("President", 0),
        ]
        assert index[0]["aliases"] == ["Author", "Writer"]

    def test_crew_detail_written_for_every_definition(
        self, populated_db, output_dir: Path
    ):
        crew_dir = dump_roles(output_dir) / "crew"
        assert {path.stem for path in crew_dir.glob("*.json")} == {
            "index",
            "playwright",
            "director",
            "stage_manager",
            "president",
        }

    def test_committee_index_lists_roles_with_ids_and_counts(
        self, populated_db, output_dir: Path
    ):
        index = read_json(dump_roles(output_dir) / "committee" / "index.json")
        assert index == [
            {
                "id": "committee_member",
                "name": "Committee Member",
                "aliases": ["Committee Members"],
                "holdingCount": 1,
            },
            {
                "id": "marketing_coordinator",
                "name": "Marketing Coordinator",
                "aliases": ["Marketing Co-ordinator"],
                "holdingCount": 1,
            },
            {"id": "president", "name": "President", "aliases": [], "holdingCount": 2},
        ]

    def test_committee_detail_written_for_every_role(
        self, populated_db, output_dir: Path
    ):
        committee_dir = dump_roles(output_dir) / "committee"
        assert {path.stem for path in committee_dir.glob("*.json")} == {
            "index",
            "committee_member",
            "marketing_coordinator",
            "president",
        }

    def test_unknown_role_is_not_dumped(self, populated_db, output_dir: Path):
        committee_dir = dump_roles(output_dir) / "committee"
        assert not (committee_dir / "unknown.json").exists()

    def test_people_duplicated_per_committee_holding(
        self, populated_db, output_dir: Path
    ):
        president = read_json(dump_roles(output_dir) / "committee" / "president.json")
        assert [holding["person"]["id"] for holding in president] == ["alice", "bob"]


class TestRoleSpec:
    def test_paths_present(self):
        assert (
            spec.SPEC["paths"]["/roles/committee/index.json"]["get"]["operationId"]
            == "getCommitteeRoles"
        )
        assert (
            spec.SPEC["paths"]["/roles/crew/index.json"]["get"]["operationId"]
            == "getCrewRoles"
        )

    def test_models_present(self):
        assert set(spec.SPEC["components"]["schemas"]["Role"]["properties"]) == {
            "id",
            "name",
            "aliases",
            "holdingCount",
        }


def test_committee_role_list_matches_schema(populated_db):
    definition = roles.RoleDefinition(name="President")
    assert roles.get_role_list(
        definition, database.PersonRoleType.COMMITTEE
    ) == schema.Role(id="president", name="President", aliases=[], holding_count=2)
