"""Wording of pydantic validation errors for the people who edit the content."""

import difflib
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel
from pydantic_core import ErrorDetails


def describe_location(loc: tuple[int | str, ...]) -> str:
    return ".".join(str(part) for part in loc) or "document"


def get_model_at(
    model: type[BaseModel], loc: tuple[int | str, ...]
) -> type[BaseModel] | None:
    """The model whose fields the key at `loc` should be one of."""
    current: type[BaseModel] | None = model
    for part in loc[:-1]:
        if current is None or isinstance(part, int):
            continue
        field = current.model_fields.get(part)
        current = find_model_in_annotation(field.annotation) if field else None
    return current


def find_model_in_annotation(annotation: Any) -> type[BaseModel] | None:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for arg in getattr(annotation, "__args__", ()):
        found = find_model_in_annotation(arg)
        if found is not None:
            return found
    return None


def describe_error(error: ErrorDetails, model: type[BaseModel] | None = None) -> str:
    """One line: where, what went wrong, and the likely fix where we can guess it."""
    location = describe_location(error["loc"])
    if error["type"] == "extra_forbidden":
        key = str(error["loc"][-1])
        message = f"{location}: unknown key `{key}`"
        nearby = get_model_at(model, error["loc"]) if model else None
        if nearby is not None:
            suggestion = suggest_key(key, nearby.model_fields)
            if suggestion:
                return f"{message}; did you mean `{suggestion}`?"
        return f"{message}; remove it, or check the spelling"
    if error["type"] == "missing":
        return f"{location}: required key is missing"
    return f"{location}: {error['msg']}"


def suggest_key(key: str, known_keys: Iterable[str]) -> str | None:
    """A known key the editor probably meant: same words reordered, or a near miss."""
    known_keys = list(known_keys)
    words = sorted(key.lower().split("_"))
    for known in known_keys:
        if sorted(known.split("_")) == words:
            return known
    matches = difflib.get_close_matches(key, known_keys, n=1, cutoff=0.6)
    return matches[0] if matches else None
