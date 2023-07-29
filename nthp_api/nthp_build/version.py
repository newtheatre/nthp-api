from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    try:
        return version("nthp_api")
    except PackageNotFoundError:
        return "unknown"
