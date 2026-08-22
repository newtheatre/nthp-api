import json
from pathlib import Path

import pytest

from nthp_api.nthp_build import database, dumper, models, schema, search, spec, venues
from nthp_api.nthp_build.parallel import DumperSharedState

SHOW_YEAR = 1999
SHOW_DECADE = 1990
YEAR_SHOW_COUNT = 12
PERSON_SHOW_COUNT = 2
GRADUATION_YEAR = 2000

CREW_ROLE_CANONICAL_NAMES = {
    "Director": "Director",
    "Co-director": "Director",
    "Stage Manager": "Stage Manager",
}


def make_show_inst(**overrides) -> database.Show:
    fields = {
        "id": "1999-00/macbeth",
        "source_path": "_shows/99_00/macbeth.md",
        "year": 1999,
        "year_id": "1999-00",
        "title": "Macbeth",
        "venue_id": "new-theatre",
        "venue_name": "New Theatre",
        "season_id": "in-house",
        "date_start": "1999-11-13",
        "primary_image": "abc12",
        "assets": "[]",
        "data": "{}",
        "plaintext": "A tragedy of ambition.",
    }
    return database.Show(**(fields | overrides))


def make_show_detail(**overrides) -> schema.ShowDetail:
    fields = {
        "id": "1999-00/macbeth",
        "title": "Macbeth",
        "year_id": "1999-00",
        "year": 1999,
        "devised": False,
        "playwright_descriptor": "by William Shakespeare",
        "playwright": schema.PlaywrightShow(
            type=schema.PlaywrightType.PLAYWRIGHT,
            name="William Shakespeare",
            descriptor="by William Shakespeare",
            student_written=False,
        ),
        "company": "Nottingham New Theatre",
        "season": "In House",
        "season_id": "in-house",
        "venue": schema.VenueRef(id="new-theatre", name="New Theatre"),
        "date_start": "1999-11-13",
        "cast": [
            schema.PersonCredit(
                role="Macbeth",
                person=schema.PersonRef(
                    id="fred_bloggs",
                    title="Fred Bloggs",
                    is_person=True,
                    has_bio=True,
                ),
            )
        ],
        "crew": [],
        "cast_incomplete": False,
        "crew_incomplete": False,
        "assets": [],
        "missing_fields": [],
        "ignore_missing": False,
        "ignore_missing_in_seasons": False,
    }
    return schema.ShowDetail(**(fields | overrides))


def make_person_detail(**overrides) -> schema.PersonDetail:
    fields = {
        "id": "fred_bloggs",
        "title": "Fred Bloggs",
        "has_bio": True,
        "submitted": False,
        "show_roles": [],
        "committee_roles": [],
        "student": False,
    }
    fields |= overrides
    return schema.PersonDetail(
        **fields,
        show_role_count=len(fields["show_roles"]),
        committee_role_count=len(fields["committee_roles"]),
    )


def make_show_roles(
    show_id: str, year_id: str, roles: list[tuple[str | None, str]]
) -> schema.PersonShowRoles:
    return schema.PersonShowRoles(
        show=schema.ShowRef(
            id=show_id,
            title="Macbeth",
            year_id=year_id,
            year=int(year_id[:4]),
        ),
        roles=[
            schema.PersonShowRoleItem(role=role, role_type=role_type)
            for role, role_type in roles
        ],
    )


def make_committee_role(year_id: str, role: str) -> schema.PersonCommitteeRole:
    return schema.PersonCommitteeRole(
        year=schema.YearRef.from_start_year(int(year_id[:4])),
        role=role,
    )


class TestShowDocument:
    def test_fields(self):
        document = search.get_show_document(make_show_inst(), make_show_detail())
        assert document.type == schema.SearchDocumentType.SHOW
        assert document.id == "1999-00/macbeth"
        assert document.title == "Macbeth"
        assert document.image_id == "abc12"
        assert document.year_id == "1999-00"
        assert document.year == SHOW_YEAR
        assert document.decade == SHOW_DECADE
        assert document.season == "In House"
        assert document.season_id == "in-house"
        assert document.venue_id == "new-theatre"
        assert document.venue_name == "New Theatre"
        assert str(document.date_start) == "1999-11-13"
        assert document.company == "Nottingham New Theatre"
        assert document.people == ["Fred Bloggs"]
        assert document.plaintext == "A tragedy of ambition."

    def test_playwright_is_the_descriptor(self):
        document = search.get_show_document(make_show_inst(), make_show_detail())
        assert document.playwright_descriptor == "by William Shakespeare"

    def test_no_playwright(self):
        document = search.get_show_document(
            make_show_inst(),
            make_show_detail(playwright=None, playwright_descriptor=None),
        )
        assert document.playwright_descriptor is None

    def test_no_venue(self):
        document = search.get_show_document(
            make_show_inst(), make_show_detail(venue=None)
        )
        assert document.venue_id is None
        assert document.venue_name is None

    def test_no_people_gives_an_empty_list(self):
        document = search.get_show_document(
            make_show_inst(), make_show_detail(cast=[], crew=[])
        )
        assert document.people == []


class TestPersonDocument:
    def test_fields(self):
        document = search.get_person_document(
            make_person_detail(
                headshot=schema.Asset(type="image", source="smugmug", id="abc12"),
                course=["English"],
                careers=["Director"],
                award="Fellowship",
            ),
            CREW_ROLE_CANONICAL_NAMES,
            has_bio=True,
            plaintext="Fred read English.",
        )
        assert document.type == schema.SearchDocumentType.PERSON
        assert document.id == "fred_bloggs"
        assert document.title == "Fred Bloggs"
        assert document.image_id == "abc12"
        assert document.has_bio is True
        assert document.course == ["English"]
        assert document.careers == ["Director"]
        assert document.award == "Fellowship"
        assert document.plaintext == "Fred read English."

    def test_person_without_a_bio(self):
        document = search.get_person_document(
            make_person_detail(), CREW_ROLE_CANONICAL_NAMES, has_bio=False
        )
        assert document.has_bio is False
        assert document.plaintext is None
        assert document.image_id is None

    def test_empty_lists_stay_lists(self):
        document = search.get_person_document(
            make_person_detail(), CREW_ROLE_CANONICAL_NAMES, has_bio=False
        )
        assert document.course == []
        assert document.careers == []
        assert document.show_roles == []
        assert document.committee_roles == []
        assert document.year_ids == []
        assert document.show_count == 0

    def test_graduation(self):
        document = search.get_person_document(
            make_person_detail(
                graduated=schema.PersonGraduated.from_grad_year(2000, estimated=True)
            ),
            CREW_ROLE_CANONICAL_NAMES,
            has_bio=True,
        )
        assert document.graduation_year_id == "1999-00"
        assert document.graduation_year == GRADUATION_YEAR
        assert document.graduation_decade == SHOW_DECADE
        assert document.graduation_estimated is True

    def test_no_graduation(self):
        document = search.get_person_document(
            make_person_detail(), CREW_ROLE_CANONICAL_NAMES, has_bio=True
        )
        assert document.graduation_year_id is None
        assert document.graduation_year is None
        assert document.graduation_decade is None
        assert document.graduation_estimated is None

    def test_show_roles_are_distinct_and_canonical(self):
        document = search.get_person_document(
            make_person_detail(
                show_roles=[
                    make_show_roles(
                        "1999-00/macbeth",
                        "1999-00",
                        [
                            ("Macbeth", schema.ShowRoleType.CAST),
                            ("Co-director", schema.ShowRoleType.CREW),
                        ],
                    ),
                    make_show_roles(
                        "2000-01/hamlet",
                        "2000-01",
                        [
                            ("Hamlet", schema.ShowRoleType.CAST),
                            ("Director", schema.ShowRoleType.CREW),
                            ("Stage Manager", schema.ShowRoleType.CREW),
                        ],
                    ),
                ]
            ),
            CREW_ROLE_CANONICAL_NAMES,
            has_bio=True,
        )
        assert document.show_roles == ["Actor", "Director", "Stage Manager"]
        assert document.show_count == PERSON_SHOW_COUNT

    def test_undefined_crew_role_passes_through(self):
        document = search.get_person_document(
            make_person_detail(
                show_roles=[
                    make_show_roles(
                        "1999-00/macbeth",
                        "1999-00",
                        [("Dramaturg", schema.ShowRoleType.CREW)],
                    )
                ]
            ),
            CREW_ROLE_CANONICAL_NAMES,
            has_bio=True,
        )
        assert document.show_roles == ["Dramaturg"]

    def test_unknown_and_unnamed_roles_dropped(self):
        document = search.get_person_document(
            make_person_detail(
                show_roles=[
                    make_show_roles(
                        "1999-00/macbeth",
                        "1999-00",
                        [
                            ("Unknown", schema.ShowRoleType.CREW),
                            (None, schema.ShowRoleType.CREW),
                        ],
                    )
                ],
                committee_roles=[make_committee_role("1999-00", "Unknown")],
            ),
            CREW_ROLE_CANONICAL_NAMES,
            has_bio=True,
        )
        assert document.show_roles == []
        assert document.committee_roles == []

    def test_committee_roles_are_distinct_and_canonical(self):
        document = search.get_person_document(
            make_person_detail(
                committee_roles=[
                    make_committee_role("1999-00", "House Manager"),
                    make_committee_role("2000-01", "Front of House Manager"),
                    make_committee_role("2000-01", "Publicity Manager"),
                ]
            ),
            CREW_ROLE_CANONICAL_NAMES,
            has_bio=True,
        )
        assert document.committee_roles == [
            "Front of House Manager",
            "Publicity Manager",
        ]

    def test_year_ids_span_shows_and_committees(self):
        document = search.get_person_document(
            make_person_detail(
                show_roles=[
                    make_show_roles(
                        "1999-00/macbeth",
                        "1999-00",
                        [("Macbeth", schema.ShowRoleType.CAST)],
                    )
                ],
                committee_roles=[
                    make_committee_role("2000-01", "Publicity Manager"),
                    make_committee_role("1999-00", "Committee Member"),
                ],
            ),
            CREW_ROLE_CANONICAL_NAMES,
            has_bio=True,
        )
        assert document.year_ids == ["1999-00", "2000-01"]


class TestVenueDocument:
    def make_record(self, **overrides) -> venues.VenueRecord:
        fields = {
            "id": "new-theatre",
            "name": "New Theatre",
            "sentinel": False,
            "venue_sort": None,
            "document": database.Venue(
                id="new-theatre",
                name="New Theatre",
                data="{}",
                plaintext="A studio theatre.",
            ),
            "document_data": models.Venue(title="New Theatre", city="Nottingham"),
            "shows": [make_show_inst()],
        }
        return venues.VenueRecord(**(fields | overrides))

    def test_fields(self):
        document = search.get_venue_document(self.make_record())
        assert document.type == schema.SearchDocumentType.VENUE
        assert document.id == "new-theatre"
        assert document.title == "New Theatre"
        assert document.city == "Nottingham"
        assert document.show_count == 1
        assert document.plaintext == "A studio theatre."

    def test_stub_venue_has_no_document_fields(self):
        document = search.get_venue_document(
            self.make_record(document=None, document_data=None, shows=[])
        )
        assert document.city is None
        assert document.plaintext is None
        assert document.show_count == 0


class TestYearDocument:
    def test_fields(self):
        document = search.get_year_document(
            schema.YearDetail(
                **dict(schema.YearRef.from_start_year(1999)),
                show_count=YEAR_SHOW_COUNT,
            )
        )
        assert document.type == schema.SearchDocumentType.YEAR
        assert document.id == "1999-00"
        assert document.title == "1999-00"
        assert document.decade == SHOW_DECADE
        assert document.show_count == YEAR_SHOW_COUNT


DOCUMENTS: list[schema.SearchDocument] = [
    search.get_year_document(
        schema.YearDetail(
            **dict(schema.YearRef.from_start_year(1999)),
            show_count=1,
        )
    ),
    search.get_show_document(make_show_inst(), make_show_detail()),
    search.get_person_document(
        make_person_detail(), CREW_ROLE_CANONICAL_NAMES, has_bio=False
    ),
    schema.SearchDocumentVenue(
        type=schema.SearchDocumentType.VENUE,
        title="New Theatre",
        id="new-theatre",
        show_count=1,
    ),
]


@pytest.fixture()
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(dumper, "OUTPUT_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def dumped(output_dir: Path) -> Path:
    dumper.dump_search_documents(
        state=DumperSharedState(search_documents=list(DOCUMENTS))
    )
    return output_dir / "search"


def read_json(path: Path):
    return json.loads(path.read_text())


class TestDumpSearchDocuments:
    def test_combined_file_holds_every_document(self, dumped: Path):
        documents = read_json(dumped / "documents.json")
        assert [(document["type"], document["id"]) for document in documents] == [
            ("person", "fred_bloggs"),
            ("show", "1999-00/macbeth"),
            ("venue", "new-theatre"),
            ("year", "1999-00"),
        ]

    @pytest.mark.parametrize(
        ("document_type", "document_id"),
        [
            ("show", "1999-00/macbeth"),
            ("person", "fred_bloggs"),
            ("venue", "new-theatre"),
            ("year", "1999-00"),
        ],
    )
    def test_per_type_file_holds_only_its_type(
        self, dumped: Path, document_type: str, document_id: str
    ):
        documents = read_json(dumped / "documents" / f"{document_type}.json")
        assert [document["id"] for document in documents] == [document_id]
        assert {document["type"] for document in documents} == {document_type}

    def test_discriminator_is_always_written(self, dumped: Path):
        documents = read_json(dumped / "documents.json")
        assert all("type" in document for document in documents)

    def test_absent_scalars_are_omitted_not_nulled(self, dumped: Path):
        person = read_json(dumped / "documents" / "person.json")[0]
        assert "graduationYearId" not in person
        assert "plaintext" not in person

    def test_empty_lists_are_written(self, dumped: Path):
        person = read_json(dumped / "documents" / "person.json")[0]
        assert person["careers"] == []
        assert person["yearIds"] == []


class TestSiteStats:
    def test_counts_the_search_corpus(self, test_db, output_dir: Path):
        dumper.dump_site_stats(
            state=DumperSharedState(search_documents=list(DOCUMENTS))
        )
        assert read_json(output_dir / "index.json")["searchDocumentCount"] == len(
            DOCUMENTS
        )


class TestSpec:
    def test_corpus_is_a_discriminated_union(self):
        items = spec.SPEC["components"]["schemas"]["SearchDocumentCollection"]["items"]
        assert items["discriminator"] == {
            "propertyName": "type",
            "mapping": {
                "show": "#/components/schemas/SearchDocumentShow",
                "person": "#/components/schemas/SearchDocumentPerson",
                "venue": "#/components/schemas/SearchDocumentVenue",
                "year": "#/components/schemas/SearchDocumentYear",
            },
        }
        assert items["oneOf"] == [
            {"$ref": "#/components/schemas/SearchDocumentShow"},
            {"$ref": "#/components/schemas/SearchDocumentPerson"},
            {"$ref": "#/components/schemas/SearchDocumentVenue"},
            {"$ref": "#/components/schemas/SearchDocumentYear"},
        ]

    @pytest.mark.parametrize("document_type", ["show", "person", "venue", "year"])
    def test_per_type_path_present(self, document_type: str):
        operation = spec.SPEC["paths"][f"/search/documents/{document_type}.json"]["get"]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith(f"SearchDocument{document_type.title()}Collection")
