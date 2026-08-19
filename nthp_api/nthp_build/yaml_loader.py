from typing import Any, NamedTuple

import yaml

MERGE_KEY = "<<"


class DuplicateKey(NamedTuple):
    key: str
    first_line: int
    duplicate_line: int


class DuplicateKeyDetectingLoader(yaml.SafeLoader):
    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        self.duplicate_keys: list[DuplicateKey] = []

    def construct_mapping(
        self, node: yaml.MappingNode, deep: bool = False
    ) -> dict[Any, Any]:
        self._record_duplicate_keys(node)
        return super().construct_mapping(node, deep=deep)

    def _record_duplicate_keys(self, node: yaml.MappingNode) -> None:
        first_seen_lines: dict[Any, int] = {}
        for key_node, _ in node.value:
            key = getattr(key_node, "value", None)
            if key == MERGE_KEY or not isinstance(key, str):
                continue
            line = key_node.start_mark.line + 1
            if key in first_seen_lines:
                self.duplicate_keys.append(
                    DuplicateKey(
                        key=key,
                        first_line=first_seen_lines[key],
                        duplicate_line=line,
                    )
                )
            else:
                first_seen_lines[key] = line


def load_yaml_detecting_duplicates(text: str) -> tuple[Any, list[DuplicateKey]]:
    loader = DuplicateKeyDetectingLoader(text)
    try:
        data = loader.get_single_data()
        return data, loader.duplicate_keys
    finally:
        loader.dispose()
