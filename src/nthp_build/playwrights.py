from slugify import slugify

from nthp_build import database


def get_playwright_id(name: str) -> str:
    return slugify(name, separator="_")


def save_playwright_show(playwright_name: str, show_id: str) -> None:
    database.PlaywrightShow.create(
        playwright_id=get_playwright_id(playwright_name),
        playwright_name=playwright_name,
        show_id=show_id,
    )
