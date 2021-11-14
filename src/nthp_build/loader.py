import contextlib
import logging
import time
from typing import Any, List, NamedTuple, Protocol, Type

import frontmatter
import peewee
from pydantic import ValidationError

from nthp_build import assets, database, models, people, playwrights, shows, years
from nthp_build.content import markdown_to_html, markdown_to_plaintext
from nthp_build.documents import DocumentPath, find_documents, load_document

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
    people.save_person_roles(
        target=path.id,
        target_type=database.PersonRoleType.CAST,
        person_list=data.cast,
    )
    people.save_person_roles(
        target=path.id,
        target_type=database.PersonRoleType.CREW,
        person_list=data.crew,
    )
    show_playwright = shows.get_show_playwright(data)
    if show_playwright and show_playwright.name:
        playwrights.save_playwright_show(
            play_name=data.title, playwright_name=show_playwright.name, show_id=path.id
        )


def load_committee(
    path: DocumentPath, document: frontmatter.Post, data: models.Committee
):
    people.save_person_roles(
        target=path.id,
        target_type=database.PersonRoleType.COMMITTEE,
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


@contextlib.contextmanager
def load_action(loader: Loader):
    log.info(f"Running loader for {loader.schema_type.__name__}")
    tick = time.perf_counter()
    yield
    tock = time.perf_counter()
    log.debug(f"Took {tock - tick:.4f} seconds")


def run_loaders():
    for loader in LOADERS:
        with load_action(loader):
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
