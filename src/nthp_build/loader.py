import functools
import logging
import time
from pathlib import Path
from typing import Any, List, NamedTuple, Protocol, Type, Union

import frontmatter
import peewee
import yaml
from pydantic import ValidationError
from pydantic_collections import BaseCollectionModel

from nthp_build import (
    assets,
    database,
    models,
    parallel,
    people,
    playwrights,
    shows,
    years,
)
from nthp_build.content import markdown_to_html, markdown_to_plaintext
from nthp_build.documents import DocumentPath, find_documents, load_document, load_yaml

log = logging.getLogger(__name__)


def load_show(path: DocumentPath, document: frontmatter.Post, data: models.Show):
    year_id = years.get_year_id_from_show_path(path)
    database.Show.create(
        id=path.id,
        source_path=path.path,
        year=years.get_year_from_year_id(year_id),
        year_id=year_id,
        title=data.title,
        season_sort=data.season_sort,
        date_start=data.date_start,
        date_end=data.date_end,
        primary_image=assets.pick_show_primary_image(data.assets)
        if data.assets
        else None,
        data=data.json(),
        content=markdown_to_html(document.content),
        plaintext=markdown_to_plaintext(document.content),
    )

    # Record person roles
    people.save_person_roles(
        target=path.id,
        target_type=database.PersonRoleType.CAST,
        target_year=years.get_year_from_year_id(year_id),
        person_list=data.cast,
    )
    people.save_person_roles(
        target=path.id,
        target_type=database.PersonRoleType.CREW,
        target_year=years.get_year_from_year_id(year_id),
        person_list=data.crew,
    )

    # Record playwright, if show has one
    show_playwright = shows.get_show_playwright(data)
    if show_playwright and show_playwright.name:
        playwrights.save_playwright_show(
            play_name=data.title,
            playwright_name=show_playwright.name,
            show_id=path.id,
            student_written=data.student_written,
        )


def load_committee(
    path: DocumentPath, document: frontmatter.Post, data: models.Committee
):
    people.save_person_roles(
        target=path.id,
        target_type=database.PersonRoleType.COMMITTEE,
        target_year=years.get_year_from_year_id(path.id),
        person_list=data.committee,
    )


def load_venue(path: DocumentPath, document: frontmatter.Post, data: models.Venue):
    database.Venue.create(
        id=path.id,
        title=data.title,
        data=data.json(),
        content=markdown_to_html(document.content),
        plaintext=markdown_to_plaintext(document.content),
    )


def load_person(path: DocumentPath, document: frontmatter.Post, data: models.Person):
    try:
        database.Person.create(
            id=data.id,
            title=data.title,
            graduated=data.graduated,
            headshot=data.headshot,
            data=data.json(),
            content=markdown_to_html(document.content),
            plaintext=markdown_to_plaintext(document.content),
        )
    except peewee.IntegrityError:
        log.error(
            f"Person ID {data.id} is already in use, please explicitly set `id` on "
            f"these people to disambiguate them."
        )


def load_history(path: DocumentPath, data: models.HistoryRecordCollection):
    for record in data:
        database.HistoryRecord.create(
            year=record.year,
            academic_year=record.academic_year,
            title=record.title,
            description=markdown_to_html(record.description),
        )


class DocumentLoaderFunc(Protocol):
    def __call__(
        self, path: DocumentPath, document: frontmatter.Post, data: Any
    ) -> None:
        pass


class DataLoaderFunc(Protocol):
    def __call__(self, path: DocumentPath, data: Any) -> None:
        pass


class Loader(NamedTuple):
    type: Type[Union[DocumentLoaderFunc, DataLoaderFunc]]
    path: Path
    schema_type: Type[Union[models.NthpModel, BaseCollectionModel[models.NthpModel]]]
    func: Union[DocumentLoaderFunc, DataLoaderFunc]


LOADERS: List[Loader] = [
    Loader(
        type=DocumentLoaderFunc,
        path=Path("_shows"),
        schema_type=models.Show,
        func=load_show,
    ),
    Loader(
        type=DocumentLoaderFunc,
        path=Path("_committees"),
        schema_type=models.Committee,
        func=load_committee,
    ),
    Loader(
        type=DocumentLoaderFunc,
        path=Path("_venues"),
        schema_type=models.Venue,
        func=load_venue,
    ),
    Loader(
        type=DocumentLoaderFunc,
        path=Path("_people"),
        schema_type=models.Person,
        func=load_person,
    ),
    Loader(
        type=DataLoaderFunc,
        path=Path("_data/history.yaml"),
        schema_type=models.HistoryRecordCollection,
        func=load_history,
    ),
]


def run_document_loader(loader: Loader):
    doc_paths = find_documents(loader.path)
    with database.db.atomic():
        for doc_path in doc_paths:
            document = load_document(doc_path.path)
            try:
                data = loader.schema_type(**{"id": doc_path.id, **document.metadata})  # type: ignore[call-arg]
            except ValidationError as e:
                log.error(f"Failed validation: {doc_path.content_path} : {e}")
                continue
            loader.func(path=doc_path, document=document, data=data)  # type: ignore[call-arg]


def run_data_loader(loader: Loader):
    with database.db.atomic():
        try:
            document_data = load_yaml(loader.path)
        except yaml.YAMLError:
            log.error(f"Failed to parse YAML: {loader.path}")
            return
        try:
            if isinstance(loader.schema_type, models.NthpModel):
                data = loader.schema_type(**document_data)  # type: ignore[call-arg]
            else:
                data = loader.schema_type(document_data)  # type: ignore[call-arg]
        except ValidationError as e:
            log.error(f"Failed validation: {loader.path} : {e}")
            return
        loader.func(
            path=DocumentPath(
                path=loader.path,
                id=loader.path.stem,
                content_path=loader.path,
                filename=loader.path.name,
                basename=loader.path.stem,
            ),
            data=data,
        )  # type: ignore[call-arg]


def run_loader(loader: Loader):
    log.info(f"Running loader for {loader.schema_type.__name__}")
    tick = time.perf_counter()
    if loader.type is DocumentLoaderFunc:
        run_document_loader(loader)
    elif loader.type is DataLoaderFunc:
        run_data_loader(loader)
    else:
        raise TypeError(f"Unhandled loader type: {loader.func}")
    tock = time.perf_counter()
    log.debug(f"Took {tock - tick:.4f} seconds")


def run_loaders():
    tasks = [functools.partial(run_loader, loader) for loader in LOADERS]
    parallel.run_tasks_in_series(tasks)
