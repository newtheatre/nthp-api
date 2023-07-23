from nthp_api.nthp_build import database, schema


def get_history_records() -> list[schema.HistoryRecord]:
    """
    Return the history record collection.
    """
    records_query = database.HistoryRecord.select()
    return [
        schema.HistoryRecord(
            year=record.year,
            year_id=record.academic_year,
            title=record.title,
            description=record.description,
        )
        for record in records_query
    ]
