from typing import List

from nthp_build import database, schema


def get_history_records() -> List[schema.HistoryRecord]:
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
