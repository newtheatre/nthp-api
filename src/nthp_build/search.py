from typing import Optional

from nthp_build import schema
from nthp_build.parallel import DumperSharedState


def add_document(
    state: DumperSharedState,
    type: schema.SearchDocumentType,
    title: str,
    id: str,
    image_id: Optional[str] = None,
    **kwargs
):
    state.search_documents.append(
        schema.SearchDocument(
            type=type, title=title, id=id, image_id=image_id, **kwargs
        )
    )
