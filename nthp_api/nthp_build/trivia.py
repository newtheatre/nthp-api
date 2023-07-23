from nthp_api.nthp_build import database, models, people, schema


def save_trivia(  # noqa: PLR0913
    *,
    target_id: str,
    target_type: str,
    target_name: str,
    target_image_id: str | None,
    target_year: int,
    trivia_list: list[models.Trivia],
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


def make_targeted_trivia(
    target_id: str, target_type: str
) -> list[schema.TargetedTrivia]:
    query = database.Trivia.select().where(
        database.Trivia.target_id == target_id,
        database.Trivia.target_type == target_type,
    )
    return [
        schema.TargetedTrivia(
            quote=row.quote,
            submitted=row.submitted,
            person_id=row.person_id,
            person_name=row.person_name,
        )
        for row in query
    ]


def make_person_trivia(person_id: str) -> list[schema.PersonTrivia]:
    query = database.Trivia.select().where(
        database.Trivia.person_id == person_id,
    )
    return [
        schema.PersonTrivia(
            quote=row.quote,
            submitted=row.submitted,
            target_id=row.target_id,
            target_type=row.target_type,
            target_name=row.target_name,
            target_image_id=row.target_image_id,
            target_year=row.target_year,
        )
        for row in query
    ]
