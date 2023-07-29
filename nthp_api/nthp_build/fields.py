from typing import Annotated, Any

from pydantic import (
    BeforeValidator,
)


def str_convert(v: Any) -> str:
    if isinstance(v, int):
        # Convert integer to string
        return str(v)
    return v


PermissiveStr = Annotated[str, BeforeValidator(str_convert)]
