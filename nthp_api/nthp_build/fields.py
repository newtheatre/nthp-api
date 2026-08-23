import calendar
import datetime
import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Annotated, Any

from pydantic import (
    BeforeValidator,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


def str_convert(v: Any) -> str:
    if isinstance(v, int):
        # Convert integer to string
        return str(v)
    return v


PermissiveStr = Annotated[str, BeforeValidator(str_convert)]

MIN_YEAR = 1900
MAX_YEAR = 2100

FUZZY_DATE_PATTERN = r"^\d{4}(-\d{2}(-\d{2})?)?$"

_FUZZY_DATE_PARSER = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


@total_ordering
@dataclass(frozen=True)
class FuzzyDate:
    """A date of year, month or day precision, as found in archive sources."""

    year: int
    month: int | None = None
    day: int | None = None

    def __post_init__(self) -> None:
        if not MIN_YEAR <= self.year <= MAX_YEAR:
            raise ValueError(
                f"Year {self.year} outside the archive range {MIN_YEAR}-{MAX_YEAR}"
            )
        if self.month is None and self.day is not None:
            raise ValueError("Day given without a month")
        if self.month is not None:
            datetime.date(self.year, self.month, self.day or 1)

    def __str__(self) -> str:
        parts = [f"{self.year:04d}"]
        if self.month is not None:
            parts.append(f"{self.month:02d}")
        if self.day is not None:
            parts.append(f"{self.day:02d}")
        return "-".join(parts)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, FuzzyDate):
            return NotImplemented
        return str(self) < str(other)

    def earliest(self) -> datetime.date:
        """The first day of the period this date covers."""
        return datetime.date(self.year, self.month or 1, self.day or 1)

    def latest(self) -> datetime.date:
        """The last day of the period this date covers."""
        if self.day is not None:
            return datetime.date(self.year, self.month, self.day)  # type: ignore[arg-type]
        if self.month is not None:
            _, last_day = calendar.monthrange(self.year, self.month)
            return datetime.date(self.year, self.month, last_day)
        return datetime.date(self.year, 12, 31)

    @classmethod
    def parse(cls, value: Any) -> "FuzzyDate":
        if isinstance(value, FuzzyDate):
            return value
        # ValueError, not TypeError: pydantic only converts ValueError into a
        # ValidationError
        if isinstance(value, bool):
            raise ValueError("Boolean is not a date")  # noqa: TRY004
        if isinstance(value, datetime.datetime):
            raise ValueError(f"Date {value} has a time component")  # noqa: TRY004
        if isinstance(value, datetime.date):
            return cls(value.year, value.month, value.day)
        if isinstance(value, int):
            return cls(value)
        if isinstance(value, str):
            return cls._parse_str(value)
        raise ValueError(f"Cannot parse a date from {type(value).__name__}")

    @classmethod
    def _parse_str(cls, value: str) -> "FuzzyDate":
        match = _FUZZY_DATE_PARSER.match(value)
        if match is None:
            raise ValueError(f"Date {value!r} is not YYYY, YYYY-MM or YYYY-MM-DD")
        year, month, day = match.groups()
        return cls(
            int(year),
            int(month) if month is not None else None,
            int(day) if day is not None else None,
        )

    @classmethod
    def to_db_value(cls, value: "FuzzyDate | None") -> str | None:
        """Reduced ISO string for storage, sortable as text."""
        return str(value) if value is not None else None

    @classmethod
    def _serialise(cls, value: Any) -> Any:
        # A union such as `FuzzyDate | bool` hands every member of the union to this
        # serialiser, so anything that isn't ours passes through untouched.
        return str(value) if isinstance(value, FuzzyDate) else value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls.parse,
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialise, when_used="json"
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string", "pattern": FUZZY_DATE_PATTERN}


FUZZY_DATE_DESCRIPTION = (
    "A date of year, month or day precision, as ISO 8601 reduced precision: "
    "`YYYY`, `YYYY-MM` or `YYYY-MM-DD`. The length of the string gives the "
    "precision the archive holds; a shorter date is not a less certain day, it is "
    "all that is recorded."
)


class _NamedFuzzyDate:
    """
    Marker giving `FuzzyDate` a schema of its own, named and referred to by `$ref`.

    Response models annotate with it so the API spec carries one `FuzzyDate`
    component that every date field refers to, rather than repeating the pattern on
    twenty fields. The ingest models keep the inline schema: a content author reads
    one document type's schema on its own.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        schema = handler(source_type)
        metadata = dict(schema.get("metadata") or {})
        # A `__get_pydantic_json_schema__` on this marker would be an annotation
        # function, whose keys pydantic leaves beside the `$ref` on every field.
        # Joining the type's own functions instead puts them on the definition.
        metadata["pydantic_js_functions"] = [
            *metadata.get("pydantic_js_functions", ()),
            cls._describe,
        ]
        return {**schema, "ref": "FuzzyDate", "metadata": metadata}  # type: ignore[typeddict-item]

    @staticmethod
    def _describe(
        schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {
            **handler(schema),
            "title": "FuzzyDate",
            "description": FUZZY_DATE_DESCRIPTION,
        }


ApiFuzzyDate = Annotated[FuzzyDate, _NamedFuzzyDate]
