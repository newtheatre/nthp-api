import pytest
import yaml

from nthp_api.nthp_build.yaml_loader import DuplicateKey, load_yaml_detecting_duplicates


def test_duplicate_top_level_key() -> None:
    data, duplicates = load_yaml_detecting_duplicates(
        "title: First\nplaywright: Someone\ntitle: Second\n"
    )
    assert duplicates == [DuplicateKey(key="title", first_line=1, duplicate_line=3)]
    assert data["title"] == "Second"


def test_duplicate_key_nested_in_list_item() -> None:
    data, duplicates = load_yaml_detecting_duplicates(
        "cast:\n"
        "  - role: Ensemble\n"
        "    name: Alice\n"
        "    role: Chorus\n"
        "  - role: Lead\n"
        "    name: Bob\n"
    )
    assert duplicates == [DuplicateKey(key="role", first_line=2, duplicate_line=4)]
    assert data["cast"][0]["role"] == "Chorus"


def test_three_occurrences_of_same_key() -> None:
    data, duplicates = load_yaml_detecting_duplicates(
        "prod_shots:\n"
        "  - one.jpg\n"
        "prod_shots:\n"
        "  - two.jpg\n"
        "prod_shots:\n"
        "  - three.jpg\n"
    )
    assert duplicates == [
        DuplicateKey(key="prod_shots", first_line=1, duplicate_line=3),
        DuplicateKey(key="prod_shots", first_line=1, duplicate_line=5),
    ]
    assert data["prod_shots"] == ["three.jpg"]


def test_no_duplicates() -> None:
    data, duplicates = load_yaml_detecting_duplicates(
        "title: A Show\ncast:\n  - name: Alice\n  - name: Bob\n"
    )
    assert duplicates == []
    assert data == {"title": "A Show", "cast": [{"name": "Alice"}, {"name": "Bob"}]}


def test_invalid_yaml_raises() -> None:
    with pytest.raises(yaml.YAMLError):
        load_yaml_detecting_duplicates("title: [unclosed\n")
