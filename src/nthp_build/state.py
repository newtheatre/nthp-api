from typing import Any, NamedTuple


class DumperSharedState(NamedTuple):
    search_documents: Any


def make_dumper_state(manager) -> DumperSharedState:
    return DumperSharedState(search_documents=manager.list())
