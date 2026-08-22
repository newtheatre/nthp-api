from nthp_api.nthp_build import database, schema, years


def get_history_records() -> list[schema.HistoryRecord]:
    """
    Return the history record collection.
    """
    records_query = database.HistoryRecord.select()
    return [
        schema.HistoryRecord(
            year=record.year,
            year_id=(
                years.get_public_year_id(
                    years.get_year_from_source_year_id(record.academic_year)
                )
                if record.academic_year
                else None
            ),
            title=record.title,
            description=record.description,
            image=(
                schema.HistoryRecordImage(href=record.image_href, alt=record.image_alt)
                if record.image_href and record.image_alt
                else None
            ),
        )
        for record in records_query
    ]
