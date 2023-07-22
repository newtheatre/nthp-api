from nthp_api.nthp_build import schema
from nthp_api.nthp_build.parallel import DumperSharedState


def add_document(
    state: DumperSharedState,
    type: schema.SearchDocumentType,
    title: str,
    id: str,
    image_id: str | None = None,
    **kwargs
):
    state.search_documents.append(
        schema.SearchDocument(
            type=type, title=title, id=id, image_id=image_id, **kwargs
        )
    )
