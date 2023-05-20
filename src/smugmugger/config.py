from pydantic import BaseSettings


class SmugMuggerSettings(BaseSettings):
    smugmug_db_uri: str = "nthp.smug.db"
    smugmug_api_key: str | None = None
    # Should we actually hit SmugMug API if needed?
    # If not, we'll just use the cached data.
    smugmug_fetch: bool = True
    smugmug_connection_limit: int = 10


settings = SmugMuggerSettings()
