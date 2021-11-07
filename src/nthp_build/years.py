from pathlib import Path

from nthp_build.documents import DocumentPath


def get_year_id(year: int) -> str:
    return f"{str(year)[-2:]}_{str(year+1)[-2:]}"


def get_year_id_from_show_path(path: DocumentPath) -> str:
    return str(Path(path.id).parent)
