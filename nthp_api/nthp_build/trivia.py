from nthp_api.nthp_build import assets, database, models, people, schema, years
from nthp_api.nthp_build.fields import FuzzyDate


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
                "submitted": FuzzyDate.to_db_value(trivia.submitted),
                "data": trivia.model_dump_json(),
            }
        )
    database.Trivia.insert_many(rows).execute()


def get_submitter_ref(
    row: database.Trivia, headshots: dict[str, str | None]
) -> schema.PersonRef | None:
    if row.person_id is None or row.person_name is None:
        return None
    return schema.PersonRef(
        id=row.person_id,
        title=row.person_name,
        is_person=True,
        has_bio=row.person_id in headshots,
        headshot=assets.get_image_ref(headshots.get(row.person_id)),
    )


def make_target_trivia(target_id: str, target_type: str) -> list[schema.Trivia]:
    """Trivia about one record, as its own document carries it."""
    query = database.Trivia.select().where(
        database.Trivia.target_id == target_id,
        database.Trivia.target_type == target_type,
    )
    rows = list(query)
    headshots = people.get_headshots_by_person_id(
        {row.person_id for row in rows if row.person_id is not None}
    )
    return [
        schema.Trivia(
            quote=row.quote,
            submitted_date=row.submitted,
            person=get_submitter_ref(row, headshots),
        )
        for row in rows
    ]


def make_trivia_target(row: database.Trivia) -> schema.TriviaTarget:
    assert row.target_year is not None, "Trivia targets are shows, which know a year"
    return schema.TriviaTarget(
        id=row.target_id,
        type=schema.TriviaTargetType(row.target_type),
        title=row.target_name,
        year_id=years.get_public_year_id(row.target_year),
        year=row.target_year,
        primary_image=assets.get_image_ref(row.target_image_id),
    )


def make_person_trivia(person_id: str) -> list[schema.Trivia]:
    """Trivia one person submitted, as their own document carries it."""
    query = database.Trivia.select().where(
        database.Trivia.person_id == person_id,
    )
    return [
        schema.Trivia(
            quote=row.quote,
            submitted_date=row.submitted,
            target=make_trivia_target(row),
        )
        for row in query
    ]
