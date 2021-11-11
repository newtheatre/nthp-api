from typing import List

from nthp_build import schema

_search_documents: List[schema.SearchDocument] = []


def add_document(type: schema.SearchDocumentType, title: str, id: str, **kwargs):
    _search_documents.append(
        schema.SearchDocument(type=type, title=title, id=id, **kwargs)
    )


def get_search_documents() -> List[schema.SearchDocument]:
    return _search_documents
