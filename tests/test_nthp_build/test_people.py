import freezegun
import pytest

from nthp_api.nthp_build import database, models, people
from nthp_api.nthp_build.schema import PersonCollaborator, PersonGraduated


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
            year_title="1995", year_decade=199, year_id="94_95", estimated=False
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
            year_title="1995", year_decade=199, year_id="94_95", estimated=True
        )

    def test_estimated_also_uses_committees(self, test_db):
        people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=1992,
            person_list=[FRED_PERSON_REF],
        )
        people.save_person_roles(
            target="01_02",
            target_type=database.PersonRoleType.COMMITTEE,
            target_year=2001,
            person_list=[FRED_PERSON_REF],
        )
        assert people.get_graduation(
            models.Person(id="fred_bloggs", title="Fred Bloggs")
        ) == PersonGraduated(
            year_title="2002", year_decade=200, year_id="01_02", estimated=True
        )

    def test_dont_assume_recent_people_have_left(self, test_db):
        people.save_person_roles(
            target=THE_TEMPEST,
            target_type=database.PersonRoleType.CAST,
            target_year=2020,
            person_list=[FRED_PERSON_REF],
        )
        graduated = PersonGraduated(
            year_title="2021", year_decade=202, year_id="20_21", estimated=True
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
