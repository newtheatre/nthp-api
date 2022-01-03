from typing import List

from nthp_build import database, models, people


def save_trivia(
    target_id: str,
    target_type: str,
    target_year: int,
    trivia_list: List[models.Trivia],
) -> None:
    rows = []
    for trivia in trivia_list:
        rows.append(
            {
                "target_id": target_id,
                "target_type": target_type,
                "target_year": target_year,
                "person_id": people.get_person_id(trivia.name) if trivia.name else None,
                "person_name": trivia.name if trivia.name else None,
                "quote": trivia.quote,
                "submitted": trivia.submitted,
                "data": trivia.json(),
            }
        )
    database.Trivia.insert_many(rows).execute()
