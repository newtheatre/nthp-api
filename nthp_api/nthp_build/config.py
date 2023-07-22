import datetime

from pydantic import BaseSettings


class Settings(BaseSettings):
    db_uri: str = "nthp.db"
    branch: str = "master"
    content_root: str

    year_start: int = 1940
    year_end: int = datetime.datetime.now().year

    # How many years to wait until guessing someone has left, if it's not been this
    # long we can assume they may still be a student.
    graduation_recency_limit: int = 2
    # What month (1-12) do people tend to graduate in?
    graduation_month: int = 6


settings = Settings()
