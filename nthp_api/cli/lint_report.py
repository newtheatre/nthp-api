"""
Rendering for `nthp lint`, written for the people who edit the content.

Each check gets a heading, a line saying what it means and what to do, and a
table of what it found. Long tails collapse to a value and a count, so a check
with hundreds of hits stays readable; `--verbose` expands them again.
"""

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from nthp_api.nthp_build.validate import Check, Finding, Severity

# Rows to show per check before collapsing to values and counts.
ROW_LIMIT = 12

SEVERITY_STYLES: dict[Severity, str] = {
    Severity.DEFECT: "bold red",
    Severity.WORTH_FIXING: "bold yellow",
    Severity.ADVISORY: "bold cyan",
}


def make_console(*, plain: bool) -> Console:
    """A console that drops colour and boxes for a log file or a CI job."""
    return Console(no_color=plain, highlight=False)


def count_by_value(findings: list[Finding]) -> list[tuple[str, int, str | None]]:
    """Findings collapsed to one row per value, commonest first."""
    counts: dict[str, int] = {}
    hints: dict[str, str | None] = {}
    for finding in findings:
        counts[finding.value] = counts.get(finding.value, 0) + 1
        hints.setdefault(finding.value, finding.hint)
    return [
        (value, count, hints[value])
        for value, count in sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    ]


def has_varying_hints(findings: list[Finding]) -> bool:
    """One hint repeated down a table is noise; the explanation already says it."""
    return len({finding.hint for finding in findings}) > 1


def check_grouping_helps(findings: list[Finding]) -> bool:
    """Worth collapsing only where the same values come up again and again."""
    distinct = len({finding.value for finding in findings})
    return len(findings) > ROW_LIMIT and distinct * 2 <= len(findings)


def make_table(*, plain: bool) -> Table:
    return Table(
        box=None if plain else box.SIMPLE_HEAD,
        pad_edge=False,
        show_edge=False,
        header_style=None if plain else "dim",
    )


def make_findings_table(findings: list[Finding], *, plain: bool) -> Table:
    """One row per finding, with the document to open where there is one."""
    table = make_table(plain=plain)
    has_paths = any(finding.source_path for finding in findings)
    has_hints = has_varying_hints(findings)
    if has_paths:
        table.add_column("File", style=None if plain else "blue", overflow="fold")
    table.add_column("Value", overflow="fold")
    if has_hints:
        table.add_column(
            "What it means", style=None if plain else "dim", overflow="fold"
        )
    for finding in findings:
        row = [finding.value]
        if has_paths:
            row.insert(0, finding.source_path or "")
        if has_hints:
            row.append(finding.hint or "")
        table.add_row(*row)
    return table


def make_grouped_table(findings: list[Finding], *, plain: bool) -> Table:
    """One row per distinct value, for a check with a long tail."""
    table = make_table(plain=plain)
    has_hints = has_varying_hints(findings)
    table.add_column("Value", overflow="fold")
    table.add_column("Count", justify="right")
    if has_hints:
        table.add_column(
            "What it means", style=None if plain else "dim", overflow="fold"
        )
    for value, count, hint in count_by_value(findings)[:ROW_LIMIT]:
        table.add_row(value, str(count), *([hint or ""] if has_hints else []))
    return table


def render_check(
    console: Console,
    check: Check,
    findings: list[Finding],
    *,
    verbose: bool,
    plain: bool,
) -> None:
    style = SEVERITY_STYLES[check.severity]
    heading = Text(f"{check.title} ({len(findings)})", style=None if plain else style)
    heading.append(f"  [{check.name}]", style="dim")
    console.print(heading)
    console.print(Text(check.explanation, style=None if plain else "dim"))
    if not findings:
        console.print(Text("  Nothing to report.", style=None if plain else "green"))
        console.print()
        return
    if verbose or not check_grouping_helps(findings):
        shown = findings if verbose else findings[:ROW_LIMIT]
        console.print(make_findings_table(shown, plain=plain))
        if not verbose and len(findings) > ROW_LIMIT:
            console.print(
                Text(
                    f"  … and {len(findings) - ROW_LIMIT} more, run with --verbose",
                    style=None if plain else "dim",
                )
            )
    else:
        console.print(make_grouped_table(findings, plain=plain))
        distinct = len(count_by_value(findings))
        if distinct > ROW_LIMIT:
            console.print(
                Text(
                    f"  … and {distinct - ROW_LIMIT} more values, run with --verbose",
                    style=None if plain else "dim",
                )
            )
    console.print()


def make_summary_table(results: dict[Check, list[Finding]], *, plain: bool) -> Table:
    table = make_table(plain=plain)
    table.add_column("Check")
    table.add_column("Findings", justify="right")
    table.add_column("Severity")
    for check, findings in results.items():
        style = None if plain else SEVERITY_STYLES[check.severity]
        table.add_row(
            check.name,
            str(len(findings)),
            Text(str(check.severity), style=style),
        )
    table.add_row(
        "total",
        str(sum(len(findings) for findings in results.values())),
        "",
        style=None if plain else "bold",
    )
    return table


def render_report(
    console: Console,
    results: dict[Check, list[Finding]],
    *,
    verbose: bool = False,
    plain: bool = False,
) -> None:
    for check, findings in results.items():
        render_check(console, check, findings, verbose=verbose, plain=plain)
    console.print(Text("Summary", style=None if plain else "bold"))
    console.print(make_summary_table(results, plain=plain))
    console.print(
        Text(
            "Nothing here fails a build; these are the archive's rough edges.",
            style=None if plain else "dim",
        )
    )
