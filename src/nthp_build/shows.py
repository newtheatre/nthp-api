import json
from typing import List

import peewee

from nthp_build import assets, database, models, people, schema


def get_show_query() -> peewee.Query:
    return database.Show.select().order_by(
        # Sort by season_sort then date_start. Means we can opt to ignore season_sort
        # within a year. However if you start using season_sort it should be added to
        # all shows.
        database.Show.season_sort,
        database.Show.date_start,
    )


def get_show_roles(person_refs: List[models.PersonRef]) -> List[schema.ShowRole]:
    query = database.Person.select(database.Person.id, database.Person.headshot).where(
        database.Person.id.in_(
            [
                people.get_person_id(person_ref.name)
                for person_ref in person_refs
                if person_ref.name is not None
            ]
        )
    )
    person_id_to_headshot = {r.id: r.headshot for r in query}
    show_roles = []
    for person_ref in person_refs:
        person_id = people.get_person_id(person_ref.name) if person_ref.name else None
        has_bio = person_id in person_id_to_headshot
        show_roles.append(
            schema.ShowRole(
                role=person_ref.role,
                person=schema.PersonList(
                    id=person_id,
                    name=person_ref.name,
                    is_person=person_ref.person,
                    headshot=person_id_to_headshot.get(person_id, None),
                    has_bio=has_bio,
                )
                if person_id
                else None,
                note=person_ref.note,
            )
        )
    return show_roles


def get_show_list_item(show_inst: database.Show) -> schema.ShowList:
    source_data = models.Show(**json.loads(show_inst.data))
    return schema.ShowList(
        id=show_inst.id,
        title=show_inst.title,
        playwright=source_data.playwright,
        adaptor=source_data.adaptor,
        devised=source_data.devised,
        season=source_data.season,
        date_start=show_inst.date_start,
        date_end=show_inst.date_end,
        primary_image=show_inst.primary_image,
    )


def get_show_detail(show_inst: database.Show) -> schema.ShowDetail:
    source_data = models.Show(**json.loads(show_inst.data))
    return schema.ShowDetail(
        id=show_inst.id,
        title=show_inst.title,
        playwright=source_data.playwright,
        devised=source_data.devised,
        improvised=source_data.improvised,
        adaptor=source_data.adaptor,
        translator=source_data.translator,
        student_written=source_data.student_written,
        company=source_data.company,
        period=source_data.period,
        season=source_data.season,
        date_start=show_inst.date_start,
        date_end=show_inst.date_end,
        cast=get_show_roles(source_data.cast),
        crew=get_show_roles(source_data.crew),
        cast_incomplete=source_data.cast_incomplete,
        cast_note=source_data.cast_note,
        crew_incomplete=source_data.crew_incomplete,
        crew_note=source_data.crew_note,
        prod_shots=source_data.prod_shots,
        assets=assets.get_show_assets(source_data),
        primary_image=show_inst.primary_image,
        content=show_inst.content,
    )
