import freezegun
import pytest

from nthp_api.nthp_build import assets, database, models, people, schema
from nthp_api.nthp_build.schema import PersonCollaborator, PersonGraduated
from nthp_api.smugmugger import SmugMugImageInfo


@pytest.mark.parametrize(
    "input,expected",
    [("Fred Bloggs", "fred_bloggs"), ("Frëd Blöggs ", "fred_bloggs")],
)
def test_get_person_id(input: str, expected: str):
    assert people.get_person_id(input) == expected


THE_TEMPEST = "the_tempest"
TITUS_ANDRONICUS = "titus_andronicus"
JULIUS_CAESAR = "julius_caesar"

FRED_PERSON_REF = models.PersonRef(
    role="A role",
    name="Fred Bloggs",
)
JOHN_PERSON_REF = models.PersonRef(
    role="Another role",
    name="John Smith",
)
ALICE_PERSON_REF = models.PersonRef(
    role="One more role",
    name="Alice Froggs",
)
ALICE_SECOND_ROLE_PERSON_REF = models.PersonRef(
    role="Yet another role",
    name="Alice Froggs",
)


class TestSavePersonRoles:
    def test_save_single(self, test_db):
        person_roles = people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[FRED_PERSON_REF],
        )
        assert len(person_roles) == 1
        assert database.PersonRole.select().count() == 1
        assert database.PersonRole.select().get().person_id == "fred_bloggs"

    def test_save_multiple(self, test_db):
        person_roles = people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[FRED_PERSON_REF, JOHN_PERSON_REF],
        )
        assert len(person_roles) == 2  # noqa: PLR2004
        assert database.PersonRole.select().count() == 2  # noqa: PLR2004
        assert (
            database.PersonRole.select()
            .where(database.PersonRole.person_id == "fred_bloggs")
            .count()
            == 1
        )
        assert (
            database.PersonRole.select()
            .where(database.PersonRole.person_id == "john_smith")
            .count()
            == 1
        )


class TestGetPersonCollaborators:
    def test_no_person(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        assert people.get_person_collaborators(person_id) == []

    def test_no_collaborators(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[FRED_PERSON_REF],
        )
        people.save_person_roles(
            target=TITUS_ANDRONICUS,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[FRED_PERSON_REF],
        )
        assert people.get_person_collaborators(person_id) == []

    def test_one_collaborator(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[FRED_PERSON_REF],
        )
        people.save_person_roles(
            target=TITUS_ANDRONICUS,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[FRED_PERSON_REF, JOHN_PERSON_REF],
        )
        assert people.get_person_collaborators(person_id) == [
            PersonCollaborator(
                person_id="john_smith",
                person_name="John Smith",
                target_ids=["titus_andronicus"],
            )
        ]

    def test_multiple_collaborators(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[FRED_PERSON_REF, ALICE_PERSON_REF],
        )
        people.save_person_roles(
            target=TITUS_ANDRONICUS,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[
                FRED_PERSON_REF,
                JOHN_PERSON_REF,
                ALICE_PERSON_REF,
            ],
        )
        people.save_person_roles(
            target=JULIUS_CAESAR,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[
                FRED_PERSON_REF,
                JOHN_PERSON_REF,
                ALICE_PERSON_REF,
            ],
        )
        assert people.get_person_collaborators(person_id) == [
            PersonCollaborator(
                person_id="alice_froggs",
                person_name="Alice Froggs",
                target_ids=["julius_caesar", "the_tempest", "titus_andronicus"],
            ),
            PersonCollaborator(
                person_id="john_smith",
                person_name="John Smith",
                target_ids=["julius_caesar", "titus_andronicus"],
            ),
        ]

    def test_multiple_roles_for_same_person(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[FRED_PERSON_REF, ALICE_PERSON_REF],
        )
        people.save_person_roles(
            target=TITUS_ANDRONICUS,
            target_type=database.PersonRoleType.CAST,
            target_year=1999,
            person_list=[
                FRED_PERSON_REF,
                JOHN_PERSON_REF,
                ALICE_PERSON_REF,
                ALICE_SECOND_ROLE_PERSON_REF,
            ],
        )

        assert people.get_person_collaborators(person_id) == [
            PersonCollaborator(
                person_id="alice_froggs",
                person_name="Alice Froggs",
                target_ids=["the_tempest", "titus_andronicus"],
            ),
            PersonCollaborator(
                person_id="john_smith",
                person_name="John Smith",
                target_ids=["titus_andronicus"],
            ),
        ]


class TestGetGraduation:
    def test_unknown(self, test_db):
        assert (
            people.get_graduation(models.Person(id="fred_bloggs", title="Fred Bloggs"))
            is None
        )

    def test_provided(self, test_db):
        assert people.get_graduation(
            models.Person(id="fred_bloggs", title="Fred Bloggs", graduated=1995)
        ) == PersonGraduated(
            year_title="1995", year_decade=199, year_id="1994-95", estimated=False
        )

    def test_estimated(self, test_db):
        people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=1992,
            person_list=[FRED_PERSON_REF],
        )
        people.save_person_roles(
            target=TITUS_ANDRONICUS,
            target_type=database.PersonRoleType.CAST,
            target_year=1994,
            person_list=[FRED_PERSON_REF],
        )
        assert people.get_graduation(
            models.Person(id="fred_bloggs", title="Fred Bloggs")
        ) == PersonGraduated(
            year_title="1995", year_decade=199, year_id="1994-95", estimated=True
        )

    def test_estimated_also_uses_committees(self, test_db):
        people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=1992,
            person_list=[FRED_PERSON_REF],
        )
        people.save_person_roles(
            target="2001-02",
            target_type=database.PersonRoleType.COMMITTEE,
            target_year=2001,
            person_list=[FRED_PERSON_REF],
        )
        assert people.get_graduation(
            models.Person(id="fred_bloggs", title="Fred Bloggs")
        ) == PersonGraduated(
            year_title="2002", year_decade=200, year_id="2001-02", estimated=True
        )

    def test_dont_assume_recent_people_have_left(self, test_db):
        people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=2020,
            person_list=[FRED_PERSON_REF],
        )
        graduated = PersonGraduated(
            year_title="2021", year_decade=202, year_id="2020-21", estimated=True
        )
        with freezegun.freeze_time("2020-01-01"):
            assert (
                people.get_graduation(
                    models.Person(id="fred_bloggs", title="Fred Bloggs")
                )
                is None
            )
        with freezegun.freeze_time("2021-01-01"):
            assert (
                people.get_graduation(
                    models.Person(id="fred_bloggs", title="Fred Bloggs")
                )
                is None
            )
        with freezegun.freeze_time("2022-05-31"):
            assert (
                people.get_graduation(
                    models.Person(id="fred_bloggs", title="Fred Bloggs")
                )
                is None
            )
        with freezegun.freeze_time("2022-06-01"):
            assert (
                people.get_graduation(
                    models.Person(id="fred_bloggs", title="Fred Bloggs")
                )
                == graduated
            )
        with freezegun.freeze_time("2023-01-01"):
            assert (
                people.get_graduation(
                    models.Person(id="fred_bloggs", title="Fred Bloggs")
                )
                == graduated
            )


class TestPersonDetailHeadshot:
    @pytest.fixture(autouse=True)
    def _clear_image_info_cache(self):
        assets.get_smugmug_image_info_map.cache_clear()
        yield
        assets.get_smugmug_image_info_map.cache_clear()

    @staticmethod
    def make_person(headshot: str | None) -> models.Person:
        return models.Person(id="fred_bloggs", title="Fred Bloggs", headshot=headshot)

    def test_no_headshot_is_none(self, test_db):
        assert people.make_person_detail(self.make_person(None)).headshot is None

    def test_headshot_becomes_an_asset(self, test_db):
        headshot = people.make_person_detail(self.make_person("abc123")).headshot
        assert headshot is not None
        assert headshot.id == "abc123"
        assert headshot.type == "image"
        assert headshot.source == "smugmug"
        assert headshot.category == "headshot"
        assert headshot.mime_type == "image/jpeg"

    def test_headshot_carries_smugmug_dimensions(self, test_db):
        saved_asset = assets.save_asset(
            target_id="fred_bloggs",
            target_type=assets.AssetTarget.PERSON,
            source=assets.AssetSource.SMUGMUG,
            type=assets.AssetType.IMAGE,
            id="abc123",
            category=assets.AssetCategory.HEADSHOT,
        )
        saved_asset.asset_smugmug_data = SmugMugImageInfo(
            width=600, height=800
        ).model_dump_json()
        saved_asset.save()
        headshot = people.make_person_detail(self.make_person("abc123")).headshot
        assert headshot is not None
        assert (headshot.width, headshot.height) == (600, 800)


class TestGetIsStudent:
    def test_no_credits_is_not_a_student(self):
        assert people.get_is_student(None, has_credits=False) is False

    def test_no_known_graduation_with_credits_is_a_student(self):
        assert people.get_is_student(None, has_credits=True) is True

    def test_graduating_in_the_future_is_a_student(self):
        with freezegun.freeze_time("2022-01-01"):
            assert (
                people.get_is_student(
                    PersonGraduated.from_year(2024, estimated=False), has_credits=True
                )
                is True
            )

    def test_graduating_later_this_year_is_a_student(self):
        with freezegun.freeze_time("2022-01-01"):
            assert (
                people.get_is_student(
                    PersonGraduated.from_year(2022, estimated=False), has_credits=True
                )
                is True
            )

    def test_graduated_earlier_this_year_is_not_a_student(self):
        with freezegun.freeze_time("2022-08-01"):
            assert (
                people.get_is_student(
                    PersonGraduated.from_year(2022, estimated=False), has_credits=True
                )
                is False
            )

    def test_graduated_long_ago_is_not_a_student(self):
        with freezegun.freeze_time("2022-01-01"):
            assert (
                people.get_is_student(
                    PersonGraduated.from_year(1995, estimated=False), has_credits=True
                )
                is False
            )


class TestMakePersonDetail:
    def test_person_fields(self, test_db):
        person = people.make_person_detail(
            models.Person(
                id="fred_bloggs",
                title="Fred Bloggs",
                course="English",
                career="Director",
                award="Fellowship",
                links=[
                    models.Link(type="Personal Website", href="https://example.com")
                ],
                news=[models.Link(type="Article", href="https://example.com/news")],
            )
        )
        assert person.course == ["English"]
        assert person.careers == ["Director"]
        assert person.award == models.Award.FELLOWSHIP
        assert person.student is False
        assert len(person.links) == 1
        assert len(person.news) == 1


class TestGetAwardHolders:
    @staticmethod
    def save_person(person: models.Person) -> None:
        database.Person.create(
            id=person.id,
            title=person.title,
            graduated=person.graduated,
            headshot=person.headshot,
            data=person.model_dump_json(),
        )

    def test_no_awards(self, test_db):
        self.save_person(
            models.Person(id="fred_bloggs", title="Fred Bloggs", graduated=1995)
        )
        assert people.get_award_holders() == {}

    def test_filed_under_the_year_graduated_in(self, test_db):
        self.save_person(
            models.Person(
                id="fred_bloggs",
                title="Fred Bloggs",
                graduated=1995,
                award="Fellowship",
                headshot="abc123",
            )
        )
        holders = people.get_award_holders()
        assert holders["1994-95"][models.Award.FELLOWSHIP] == [
            schema.PersonAwardHolder(
                id="fred_bloggs", title="Fred Bloggs", headshot="abc123"
            )
        ]

    def test_awards_kept_apart_and_sorted_by_surname(self, test_db):
        self.save_person(
            models.Person(
                id="zoe_adams", title="Zoe Adams", graduated=1995, award="Fellowship"
            )
        )
        self.save_person(
            models.Person(
                id="alice_young",
                title="Alice Young",
                graduated=1995,
                award="Fellowship",
            )
        )
        self.save_person(
            models.Person(
                id="fred_bloggs",
                title="Fred Bloggs",
                graduated=1995,
                award="Commendation",
            )
        )
        holders = people.get_award_holders()["1994-95"]
        assert [person.title for person in holders[models.Award.FELLOWSHIP]] == [
            "Zoe Adams",
            "Alice Young",
        ]
        assert [person.title for person in holders[models.Award.COMMENDATION]] == [
            "Fred Bloggs"
        ]

    def test_unknown_graduation_year_warns(
        self, test_db, caplog: pytest.LogCaptureFixture
    ):
        self.save_person(
            models.Person(id="fred_bloggs", title="Fred Bloggs", award="Fellowship")
        )
        assert people.get_award_holders() == {}
        assert "no known graduation year" in caplog.text
