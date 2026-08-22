import datetime
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

ACADEMIC_YEAR_START_MONTH = 9


def get_current_year_end(today: datetime.date | None = None) -> int:
    """
    Exclusive upper bound on the academic years to build.

    Academic years run September to August and are keyed by their start year, so
    from September the year that has just begun needs including.
    """
    today = today or datetime.date.today()
    if today.month >= ACADEMIC_YEAR_START_MONTH:
        return today.year + 1
    return today.year


class Settings(BaseSettings):
    db_uri: str = "nthp.db"
    # GitHub Actions sets these three itself, on every run of a workflow.
    branch: str = Field(
        default="master", validation_alias=AliasChoices("BRANCH", "GITHUB_REF_NAME")
    )
    build_number: str | None = Field(default=None, validation_alias="GITHUB_RUN_NUMBER")
    commit: str | None = Field(default=None, validation_alias="GITHUB_SHA")
    content_root: Path

    year_start: int = 1940
    year_end: int = Field(default_factory=get_current_year_end)

    # How many years to wait until guessing someone has left, if it's not been this
    # long we can assume they may still be a student.
    graduation_recency_limit: int = 2
    # What month (1-12) do people tend to graduate in?
    graduation_month: int = 6

    # Mirrors the content repo's _config.yml: a show with this many crew or fewer
    # counts as missing its crew.
    show_low_crew: int = 5
    # Seasons whose shows are not expected to be fully documented, by season id.
    ignore_missing_in_season_ids: set[str] = Field(
        default_factory=lambda: {"external", "postgrads", "stuff"}
    )


settings = Settings()
