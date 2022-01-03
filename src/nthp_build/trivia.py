from typing import List, Optional

from nthp_build import database, models, people, schema


def save_trivia(
    *,
    target_id: str,
    target_type: str,
    target_name: str,
    target_image_id: Optional[str],
    target_year: int,
    trivia_list: List[models.Trivia],
) -> None:
    rows = []
    for trivia in trivia_list:
        rows.append(
            {
                "target_id": target_id,
                "target_type": target_type,
                "target_name": target_name,
                "target_image_id": target_image_id,
                "target_year": target_year,
                "person_id": people.get_person_id(trivia.name) if trivia.name else None,
                "person_name": trivia.name if trivia.name else None,
                "quote": trivia.quote,
                "submitted": trivia.submitted,
                "data": trivia.json(),
            }
        )
    database.Trivia.insert_many(rows).execute()
