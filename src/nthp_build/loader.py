import logging
from typing import Any, List, NamedTuple, Protocol, Type

import frontmatter
import peewee
from pydantic import ValidationError

from nthp_build import database, models, people, years
from nthp_build.documents import DocumentPath, find_documents, load_document
from nthp_build.people import save_person_roles

log = logging.getLogger(__name__)


def load_show(path: DocumentPath, document: frontmatter.Post, data: models.Show):
    database.Show.create(
        id=path.id,
        year_id=years.get_year_id_from_show_path(path),
        title=data.title,
        data=data.json(),
        source_path=path.path,
        content=document.content,
    )
    save_person_roles(
        target=path.id,
        target_type=database.PersonRoleType.CAST,
        person_list=data.cast,
    )
    save_person_roles(
        target=path.id,
        target_type=database.PersonRoleType.CREW,
        person_list=data.crew,
    )


def load_committee(
    path: DocumentPath, document: frontmatter.Post, data: models.Committee
):
    save_person_roles(
        target=path.id,
        target_type=database.PersonRoleType.COMMITTEE,
        person_list=data.committee,
    )


def load_venue(path: DocumentPath, document: frontmatter.Post, data: models.Venue):
    database.Venue.create(
        id=path.id,
        title=data.title,
        data=data.json(),
    )


def load_person(path: DocumentPath, document: frontmatter.Post, data: models.Person):
    try:
        database.Person.create(
            id=data.id,
            title=data.title,
            graduated=data.graduated,
            headshot=data.headshot,
            data=data.json(),
            content=document.content,
        )
    except peewee.IntegrityError:
        log.error(
            f"Person ID {data.id} is already in use, please explicitly set `id` on "
            f"these people to disambiguate them."
        )


class LoaderFunc(Protocol):
    def __call__(
        self, path: DocumentPath, document: frontmatter.Post, data: Any
    ) -> None:
        pass


class Loader(NamedTuple):
    content_directory: str
    schema_type: Type[models.NthpModel]
    func: LoaderFunc


LOADERS: List[Loader] = [
    Loader(
        content_directory="_shows",
        schema_type=models.Show,
        func=load_show,
    ),
    Loader(
        content_directory="_committees",
        schema_type=models.Committee,
        func=load_committee,
    ),
    Loader(
        content_directory="_venues",
        schema_type=models.Venue,
        func=load_venue,
    ),
    Loader(
        content_directory="_people",
        schema_type=models.Person,
        func=load_person,
    ),
]


def run_loaders():
    for loader in LOADERS:
        log.info(f"Running loader for {loader.schema_type.__name__}")
        doc_paths = find_documents(loader.content_directory)
        with database.db.atomic():
            for doc_path in doc_paths:
                document = load_document(doc_path.path)
                try:
                    data = loader.schema_type(
                        **{"id": doc_path.id, **document.metadata}
                    )
                except ValidationError as e:
                    log.error(f"Failed validation: {doc_path.content_path} : {e}")
                    continue
                loader.func(path=doc_path, document=document, data=data)
