import pytest

from nthp_build import database, models, people
from nthp_build.schema import PersonCollaborator


@pytest.mark.parametrize(
    "input,expected",
    [("Fred Bloggs", "fred_bloggs"), ("Frëd Blöggs ", "fred_bloggs")],
)
def test_get_person_id(input: str, expected: str):
    assert people.get_person_id(input) == expected


THE_TEMPEST = "the_tempest"
TITUS_ANDRONICUS = "titus_andronicus"
JULIUS_CAESAR = "julius_caesar"


class TestGetPersonCollaborators:
    def test_no_person(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        assert people.get_person_collaborators(person_id) == set()

    def test_no_collaborators(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        people.save_person_roles(
            THE_TEMPEST,
            database.PersonRoleType.CAST,
            [
                models.PersonRef(
                    role="Prospero",
                    name="Fred Bloggs",
                )
            ],
        )
        people.save_person_roles(
            TITUS_ANDRONICUS,
            database.PersonRoleType.CAST,
            [
                models.PersonRef(
                    role="Quintus",
                    name="Fred Bloggs",
                )
            ],
        )
        assert people.get_person_collaborators(person_id) == set()

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

    def test_one_collaborator(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        people.save_person_roles(
            THE_TEMPEST,
            database.PersonRoleType.CAST,
            [self.FRED_PERSON_REF],
        )
        people.save_person_roles(
            TITUS_ANDRONICUS,
            database.PersonRoleType.CAST,
            [self.FRED_PERSON_REF, self.JOHN_PERSON_REF],
        )
        assert people.get_person_collaborators(person_id) == {
            PersonCollaborator(
                person_id="john_smith",
                person_name="John Smith",
                target_ids={"titus_andronicus"},
            )
        }

    def test_multiple_collaborators(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        people.save_person_roles(
            THE_TEMPEST,
            database.PersonRoleType.CAST,
            [self.FRED_PERSON_REF, self.ALICE_PERSON_REF],
        )
        people.save_person_roles(
            TITUS_ANDRONICUS,
            database.PersonRoleType.CAST,
            [self.FRED_PERSON_REF, self.JOHN_PERSON_REF, self.ALICE_PERSON_REF],
        )
        people.save_person_roles(
            JULIUS_CAESAR,
            database.PersonRoleType.CAST,
            [self.FRED_PERSON_REF, self.JOHN_PERSON_REF, self.ALICE_PERSON_REF],
        )
        assert people.get_person_collaborators(person_id) == {
            PersonCollaborator(
                person_id="john_smith",
                person_name="John Smith",
                target_ids={"julius_caesar", "titus_andronicus"},
            ),
            PersonCollaborator(
                person_id="alice_froggs",
                person_name="Alice Froggs",
                target_ids={"julius_caesar", "the_tempest", "titus_andronicus"},
            ),
        }

    def test_multiple_roles_for_same_person(self, test_db):
        person_id = people.get_person_id("Fred Bloggs")
        people.save_person_roles(
            THE_TEMPEST,
            database.PersonRoleType.CAST,
            [self.FRED_PERSON_REF, self.ALICE_PERSON_REF],
        )
        people.save_person_roles(
            TITUS_ANDRONICUS,
            database.PersonRoleType.CAST,
            [
                self.FRED_PERSON_REF,
                self.JOHN_PERSON_REF,
                self.ALICE_PERSON_REF,
                self.ALICE_SECOND_ROLE_PERSON_REF,
            ],
        )

        assert people.get_person_collaborators(person_id) == {
            PersonCollaborator(
                person_id="john_smith",
                person_name="John Smith",
                target_ids={"titus_andronicus"},
            ),
            PersonCollaborator(
                person_id="alice_froggs",
                person_name="Alice Froggs",
                target_ids={"the_tempest", "titus_andronicus"},
            ),
        }
