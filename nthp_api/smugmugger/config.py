from pydantic_settings import BaseSettings


class SmugMuggerSettings(BaseSettings):
    smugmug_db_uri: str = "nthp.smug.db"
    smugmug_api_key: str | None = None
    # Should we actually hit SmugMug API if needed?
    # If not, we'll just use the cached data.
    smugmug_fetch: bool = True
    smugmug_connection_limit: int = 10
    smugmug_timeout_seconds: float = 30.0
    smugmug_retry_attempts: int = 4
    smugmug_retry_backoff_seconds: float = 1.0


settings = SmugMuggerSettings()
