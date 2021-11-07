import datetime

from pydantic import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    branch: str = "master"
    year_start: int = 1940
    year_end: int = datetime.datetime.now().year


settings = Settings()
