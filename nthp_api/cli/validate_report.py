"""
Rendering for `nthp validate`, written for whoever is editing the file.

A file with nothing wrong takes one line; a file with problems gets a table of
where, what, and the value at fault. The summary at the end is what a script
reads if it is not reading the exit code.
"""

from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from nthp_api.nthp_build.content_check import FileResult, Problem

# Values longer than this are cut; the file itself has the rest.
VALUE_LIMIT = 60


def make_console(*, plain: bool) -> Console:
    """A console that drops colour and boxes for a log file or a CI job."""
    return Console(no_color=plain, highlight=False)


def relative_to_cwd(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def truncate(value: str) -> str:
    return value if len(value) <= VALUE_LIMIT else value[: VALUE_LIMIT - 1] + "…"


def make_problems_table(problems: list[Problem], *, plain: bool) -> Table:
    table = Table(
        box=None if plain else box.SIMPLE_HEAD,
        pad_edge=False,
        show_edge=False,
        header_style=None if plain else "dim",
    )
    table.add_column("Where", style=None if plain else "yellow", overflow="fold")
    table.add_column("Problem", overflow="fold")
    table.add_column("Value", style=None if plain else "dim", overflow="fold")
    for problem in problems:
        table.add_row(
            problem.location,
            problem.message,
            truncate(problem.value) if problem.value else "",
        )
    return table


def render_result(console: Console, result: FileResult, *, plain: bool) -> None:
    heading = Text(relative_to_cwd(result.path), style=None if plain else "bold blue")
    if result.document_type is not None:
        heading.append(f"  [{result.document_type.name}]", style="dim")
    console.print(heading)
    console.print(make_problems_table(result.problems, plain=plain))
    console.print()


def render_report(
    console: Console,
    results: list[FileResult],
    *,
    verbose: bool = False,
    plain: bool = False,
) -> None:
    failed = [result for result in results if not result.ok]
    for result in results:
        if result.ok:
            if verbose:
                console.print(
                    Text(
                        f"{relative_to_cwd(result.path)} — no problems",
                        style=None if plain else "green",
                    )
                )
            continue
        render_result(console, result, plain=plain)
    summary = (
        f"{len(results)} file{'' if len(results) == 1 else 's'} checked, "
        f"{len(failed)} with problems"
    )
    console.print(
        Text(summary, style=None if plain else ("bold red" if failed else "bold green"))
    )
