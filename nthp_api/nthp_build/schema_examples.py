"""
Whole-document examples for the response models.

A spec renderer builds its sample response from the schema, so a document of
nullable fields renders as a wall of `null` and empty lists. These examples give
each detail document one realistic record instead, drawn from a 2024-25 staging of
Macbeth that never happened. `tests/test_nthp_build/test_schema_examples.py`
validates every one against its model, so they cannot drift from the schema.

Keys are the camelCase aliases a consumer sees, and ids match the field-level
examples in `schema.py`.
"""

from typing import Any

MACBETH_IMAGE = {"id": "qABC123", "width": 1600, "height": 1200}

MACBETH_REF = {
    "id": "2024-25/macbeth",
    "title": "Macbeth",
    "yearId": "2024-25",
    "year": 2024,
    "primaryImage": MACBETH_IMAGE,
}

DIRECTOR_REF = {
    "id": "charlie_carey",
    "title": "Charlie Carey",
    "isPerson": True,
    "hasBio": True,
    "headshot": {"id": "qDEF456", "width": 800, "height": 800},
}


def _person_ref(person_id: str, title: str, *, has_bio: bool = False) -> dict[str, Any]:
    return {"id": person_id, "title": title, "isPerson": True, "hasBio": has_bio}


SHOW_DETAIL = {
    "id": "2024-25/macbeth",
    "title": "Macbeth",
    "yearId": "2024-25",
    "year": 2024,
    "season": "In House",
    "seasonId": "in-house",
    "venue": {"id": "nottingham-new-theatre", "name": "Nottingham New Theatre"},
    "dateStart": "2024-11-13",
    "dateEnd": "2024-11-16",
    "primaryImage": MACBETH_IMAGE,
    "playwrightDescriptor": "by William Shakespeare",
    "playwright": {
        "id": "william_shakespeare",
        "name": "William Shakespeare",
        "type": "playwright",
        "descriptor": "by William Shakespeare",
        "studentWritten": False,
    },
    "devised": False,
    "play": {"id": "macbeth", "title": "Macbeth"},
    "period": "Autumn",
    "tour": [
        {
            "venue": "Lakeside Arts",
            "dateStart": "2024-11-22",
            "dateEnd": "2024-11-23",
            "note": "Two nights as part of the Lakeside student season",
        }
    ],
    "cast": [
        {
            "role": "Macbeth",
            "person": _person_ref("ben_adeniji", "Ben Adeniji", has_bio=True),
        },
        {"role": "Lady Macbeth", "person": _person_ref("holly_howell", "Holly Howell")},
        {"role": "Banquo", "person": _person_ref("juhi_andon", "Juhi Andon")},
        {
            "role": "First Witch",
            "person": _person_ref("ali_seaborne", "Ali Seaborne"),
            "note": "Also understudied Lady Macbeth",
        },
    ],
    "crew": [
        {"role": "Director", "person": DIRECTOR_REF},
        {
            "role": "Producer",
            "person": _person_ref("laura_denison", "Laura Denison", has_bio=True),
        },
        {
            "role": "Lighting Designer",
            "person": _person_ref("rosa_williams", "Rosa Williams"),
        },
        {"role": "Sound Designer", "person": _person_ref("ben_canning", "Ben Canning")},
    ],
    "castIncomplete": False,
    "crewIncomplete": False,
    "assets": [
        {
            "id": "qABC123",
            "width": 1600,
            "height": 1200,
            "type": "image",
            "source": "smugmug",
            "mimeType": "image/jpeg",
            "category": "poster",
            "title": "Poster",
            "uploadedAt": "2024-10-28T18:02:11Z",
        },
        {
            "id": "qGHI789",
            "type": "other",
            "source": "file",
            "mimeType": "application/pdf",
            "category": "programme",
            "title": "Programme",
            "page": 1,
        },
    ],
    "missingFields": ["excerpt"],
    "ignoreMissing": False,
    "links": [
        {
            "type": "Review",
            "isNews": True,
            "href": "https://impactnottingham.com/2024/11/review-macbeth/",
            "hrefSnapshot": "https://archive.is/abc12",
            "title": "Review: Macbeth",
            "date": "2024-11-15",
            "publisher": "Impact Magazine",
            "rating": "4/5",
            "quote": "A triumph from start to finish",
        }
    ],
    "ignoreMissingInSeasons": False,
    "previous": {
        "id": "2024-25/the_sinking_place",
        "title": "The Sinking Place",
        "yearId": "2024-25",
        "year": 2024,
    },
    "next": {
        "id": "2024-25/the_duchess_of_malfi",
        "title": "The Duchess of Malfi",
        "yearId": "2024-25",
        "year": 2024,
    },
    "trivia": [
        {
            "quote": "The cauldron was a wheelie bin borrowed from the SU and never "
            "returned.",
            "submittedDate": "2025-01",
            "person": _person_ref("laura_denison", "Laura Denison", has_bio=True),
        }
    ],
    "content": "<p>A studio staging of the Scottish play, run without an interval.</p>",
}

PERSON_DETAIL = {
    "id": "charlie_carey",
    "title": "Charlie Carey",
    "hasBio": True,
    "headshot": {
        "id": "qDEF456",
        "width": 800,
        "height": 800,
        "type": "image",
        "source": "smugmug",
        "mimeType": "image/jpeg",
        "category": "headshot",
        "title": "Headshot",
        "uploadedAt": "2024-10-02T09:14:52Z",
    },
    "graduated": {
        "id": "2025-26",
        "title": "2025/26",
        "startYear": 2025,
        "gradYear": 2026,
        "decade": 2020,
        "estimated": False,
    },
    "submitted": True,
    "submittedDate": "2022-01",
    "showRoleCount": 7,
    "committeeRoleCount": 2,
    "showRoles": [
        {
            "show": MACBETH_REF,
            "roles": [
                {"role": "Director", "roleType": "crew"},
                {"role": "Second Murderer", "roleType": "cast"},
            ],
        }
    ],
    "committeeRoles": [
        {
            "year": {
                "id": "2024-25",
                "title": "2024/25",
                "startYear": 2024,
                "gradYear": 2025,
                "decade": 2020,
            },
            "role": "Publicity Manager",
        }
    ],
    "course": ["English and Philosophy"],
    "award": "Best Director",
    "careers": ["Assistant director, Nottingham Playhouse"],
    "student": True,
    "links": [
        {
            "type": "Twitter",
            "isNews": False,
            "href": "https://twitter.com/nnt_official",
            "username": "nnt_official",
        }
    ],
    "news": [
        {
            "type": "Article",
            "isNews": True,
            "href": "https://impactnottingham.com/2025/03/directing-macbeth/",
            "hrefSnapshot": "https://archive.is/def34",
            "title": "Directing Macbeth on a student budget",
            "date": "2025-03-04",
            "publisher": "Impact Magazine",
        }
    ],
    "trivia": [
        {
            "quote": "I only auditioned because the queue for the bar was too long.",
            "submittedDate": "2025-02-14",
            "target": {
                "id": "2024-25/macbeth",
                "title": "Macbeth",
                "yearId": "2024-25",
                "year": 2024,
                "primaryImage": MACBETH_IMAGE,
                "type": "show",
            },
        }
    ],
    "content": "<p>Directed Macbeth in 2024/25 and sat on committee twice.</p>",
}

SHOW_LIST_ITEM = {
    "id": "2024-25/macbeth",
    "title": "Macbeth",
    "yearId": "2024-25",
    "year": 2024,
    "season": "In House",
    "seasonId": "in-house",
    "venue": {"id": "nottingham-new-theatre", "name": "Nottingham New Theatre"},
    "dateStart": "2024-11-13",
    "dateEnd": "2024-11-16",
    "primaryImage": MACBETH_IMAGE,
    "playwrightDescriptor": "by William Shakespeare",
    "playwright": {
        "id": "william_shakespeare",
        "name": "William Shakespeare",
        "type": "playwright",
        "descriptor": "by William Shakespeare",
        "studentWritten": False,
    },
    "devised": False,
}

YEAR_DETAIL = {
    "id": "2024-25",
    "title": "2024/25",
    "startYear": 2024,
    "gradYear": 2025,
    "decade": 2020,
    "showCount": 24,
    "shows": [SHOW_LIST_ITEM],
    "committee": [
        {"role": "President", "person": DIRECTOR_REF},
        {
            "role": "Treasurer",
            "person": _person_ref("laura_denison", "Laura Denison", has_bio=True),
        },
    ],
    "fellows": [_person_ref("ben_adeniji", "Ben Adeniji", has_bio=True)],
    "commendations": [_person_ref("holly_howell", "Holly Howell")],
}

SEASON_DETAIL = {
    "id": "in-house",
    "name": "In House",
    "aliases": ["In-House", "In house"],
    "showCount": 12,
    "shows": [SHOW_LIST_ITEM],
}

VENUE_DETAIL = {
    "id": "nottingham-new-theatre",
    "name": "Nottingham New Theatre",
    "showCount": 1420,
    "group": "University Park",
    "hasRecord": True,
    "sentinel": False,
    "built": 1979,
    "location": {"lat": 52.9385, "lon": -1.1957},
    "city": "Nottingham",
    "assets": [
        {
            "id": "qJKL012",
            "width": 2000,
            "height": 1333,
            "type": "image",
            "source": "smugmug",
            "mimeType": "image/jpeg",
            "title": "The auditorium",
            "uploadedAt": "2023-06-11T15:40:00Z",
        }
    ],
    "links": [
        {
            "type": "Website",
            "isNews": False,
            "href": "https://newtheatre.org.uk/",
            "title": "New Theatre",
        }
    ],
    "shows": [SHOW_LIST_ITEM],
    "content": "<p>The society's own theatre, on University Park campus.</p>",
}

SITE_STATS = {
    "buildTime": "2025-08-23T01:12:45.678901Z",
    "branch": "master",
    "apiVersion": "0.4.2",
    "commit": "1f0a9c2e0c0a4a1b8d3f6e5c4b3a29180706f5e4",
    "buildNumber": "42",
    "showCount": 1420,
    "personCount": 4820,
    "personWithBioCount": 613,
    "personWithHeadshotCount": 402,
    "showWithImageCount": 984,
    "venueCount": 63,
    "yearCount": 85,
    "firstYearId": "1940-41",
    "latestYearId": "2024-25",
    "creditCount": 21840,
    "triviaCount": 318,
    "searchDocumentCount": 6388,
}

ON_THIS_DAY_SHOW = {
    "id": "2024-25/macbeth",
    "title": "Macbeth",
    "yearId": "2024-25",
    "year": 2024,
    "primaryImage": MACBETH_IMAGE,
    "dateStart": "2024-11-13",
    "dateEnd": "2024-11-16",
}

SEARCH_DOCUMENT_SHOW = {
    "type": "show",
    "title": "Macbeth",
    "id": "2024-25/macbeth",
    "imageId": "qABC123",
    "yearId": "2024-25",
    "year": 2024,
    "decade": 2020,
    "season": "In House",
    "seasonId": "in-house",
    "venueId": "nottingham-new-theatre",
    "venueName": "Nottingham New Theatre",
    "dateStart": "2024-11-13",
    "playwrightDescriptor": "by William Shakespeare",
    "people": ["Charlie Carey", "Ben Adeniji", "Holly Howell"],
    "plaintext": "A studio staging of the Scottish play, run without an interval.",
}
