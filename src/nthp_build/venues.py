from slugify import slugify


def get_venue_id(name: str) -> str:
    return slugify(name, separator="-")
