from nthp_build import schema
from nthp_build.state import DumperSharedState


def add_document(
    state: DumperSharedState,
    type: schema.SearchDocumentType,
    title: str,
    id: str,
    **kwargs
):
    state.search_documents.append(
        schema.SearchDocument(type=type, title=title, id=id, **kwargs)
    )
