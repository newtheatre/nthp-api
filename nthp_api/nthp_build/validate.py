"""
Checks over the loaded database, once every document is in it.

Cross-document defects — two spellings of one venue, two names behind one id —
cannot be seen while a single document is loading, so they are checked here,
between the loaders and the dump.

Build checks report defects that should be fixed, as ERRORs naming the documents
at fault. Lint checks report the expected and the advisory, and are rendered by
`nthp lint` rather than alarming a build.
"""

import json
import logging
import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from difflib import SequenceMatcher
from enum import StrEnum
from typing import NamedTuple

from nthp_api.nthp_build import assets, database, links, models, people, roles

log = logging.getLogger(__name__)

MAX_YEARS_AFTER_LAST_CREDIT = 10
# A break this long between one id's credits reads as two people, not one career.
MERGE_GAP_YEARS = 8
# How far from a documented graduation year that person's credits may still run.
DOCUMENTED_GRADUATION_MARGIN = 6
# How alike two forenames behind one surname must be to read as one person.
FORENAME_SIMILARITY_LIMIT = 0.6
FORENAME_SHARED_PREFIX = 2

SENTINEL_VENUE_IDS = frozenset({"unknown", "youtube"})


class Severity(StrEnum):
    """How much a finding asks of the reader."""

    DEFECT = "defect"
    WORTH_FIXING = "worth fixing"
    ADVISORY = "advisory"


class Finding(NamedTuple):
    """
    One thing a check found.

    `value` is what is at fault — a name, an id, a field — and `hint` says what
    it costs the archive or what to do about it. `source_path` is the document
    it lives in, where one document owns it.
    """

    value: str
    source_path: str | None = None
    hint: str | None = None

    def __str__(self) -> str:
        located = (
            f"{self.source_path}: {self.value}" if self.source_path else self.value
        )
        return f"{located} — {self.hint}" if self.hint else located


class Check(NamedTuple):
    """
    One check, and how `nthp lint` should introduce it.

    `note` is for what the check chose not to report: cases it suppressed on
    purpose, shown under `--verbose` so the suppression is visible.
    """

    name: str
    title: str
    explanation: str
    severity: Severity
    func: Callable[[], list[Finding]]
    note: Callable[[], str | None] | None = None


PLACEHOLDER_CONTENT_CHECK = "placeholder-content"
SCALAR_LIST_FIELD_CHECK = "scalar-lists"

PLACEHOLDER_CONTENT_PATTERN = re.compile(r"^\s*(<!--.*?-->\s*)+$", re.DOTALL)


def record_finding(check: str, value: str, source_path: str, hint: str) -> None:
    """
    Note something only the loader can see, for `nthp lint` to report later.

    The authored shape of a document is gone by the time it reaches sqlite: a
    coerced value and a placeholder body both look ordinary from there.
    """
    database.LoadFinding.create(
        check=check, value=value, source_path=source_path, hint=hint
    )


def get_recorded_findings(check: str) -> list[Finding]:
    return [
        Finding(row.value, row.source_path, row.hint)
        for row in database.LoadFinding.select()
        .where(database.LoadFinding.check == check)
        .order_by(database.LoadFinding.source_path)
    ]


def check_content_is_not_a_placeholder(content: str, source_path: str) -> None:
    if content.strip() and PLACEHOLDER_CONTENT_PATTERN.match(content):
        record_finding(
            PLACEHOLDER_CONTENT_CHECK,
            "HTML comment only",
            source_path,
            "write the body, or leave the file without one",
        )


def pluralise(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def get_person_models() -> Iterable[tuple[database.Person, models.Person]]:
    for person_inst in database.Person.select():
        yield person_inst, models.Person(**json.loads(person_inst.data))


def get_show_models() -> Iterable[tuple[database.Show, models.Show]]:
    for show_inst in database.Show.select():
        yield show_inst, models.Show(**json.loads(show_inst.data))


def check_venue_spellings() -> list[Finding]:
    """A venue id authored under several spellings takes the commonest, arbitrarily."""
    spellings: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for show in database.Show.select().where(
        database.Show.venue_id.is_null(False),
        database.Show.venue_name.is_null(False),
    ):
        spellings[show.venue_id][show.venue_name].append(show.source_path)
    return [
        Finding(
            venue_id,
            hint="authored as "
            + "; ".join(
                f"{name!r} in {sorted(paths)[0]}"
                + (f" and {len(paths) - 1} more" if len(paths) > 1 else "")
                for name, paths in sorted(names.items())
            ),
        )
        for venue_id, names in sorted(spellings.items())
        if len(names) > 1
    ]


def check_award_graduation() -> list[Finding]:
    """An award is filed under the year its holder graduated, so it needs one."""
    return [
        Finding(
            str(model.award),
            person_inst.source_path,
            "no known or estimable graduation year, so the award is on no year page",
        )
        for person_inst, model in get_person_models()
        if model.award is not None and people.get_graduation(model) is None
    ]


def _duplicate_names_by_id(
    id_field: str, name_field: str
) -> dict[str, dict[str, list[str]]]:
    names: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in database.PlaywrightShow.select():
        names[getattr(row, id_field)][getattr(row, name_field)].append(row.show_id)
    return {id: by_name for id, by_name in names.items() if len(by_name) > 1}


def format_shared_names(names: dict[str, list[str]]) -> str:
    return "shared by " + ", ".join(
        f"{name!r} ({shows[0]})" for name, shows in sorted(names.items())
    )


def check_playwright_ids() -> list[Finding]:
    """Two spellings of a writer's name collide as one id, dumped twice over."""
    return [
        Finding(playwright_id, hint=format_shared_names(names))
        for playwright_id, names in sorted(
            _duplicate_names_by_id("playwright_id", "playwright_name").items()
        )
    ]


def check_play_ids() -> list[Finding]:
    """Two spellings of a play's title collide as one id, dumped twice over."""
    return [
        Finding(play_id, hint=format_shared_names(names))
        for play_id, names in sorted(
            _duplicate_names_by_id("play_id", "play_name").items()
        )
    ]


BUILD_CHECKS: list[Check] = [
    Check(
        "venue-spellings",
        "Venue spellings",
        "One venue authored under several names; the commonest wins, arbitrarily. "
        "Settle on one spelling across the shows.",
        Severity.DEFECT,
        check_venue_spellings,
    ),
    Check(
        "award-graduation",
        "Awards without a graduation year",
        "Awards are listed under the year their holder graduated. Add `graduated` "
        "to the person, or credit them on a show so it can be estimated.",
        Severity.DEFECT,
        check_award_graduation,
    ),
    Check(
        "playwright-ids",
        "Playwright ids shared by two names",
        "Two spellings of a writer's name make one id, which the playwright index "
        "then lists twice. Spell the name the same way in every show.",
        Severity.DEFECT,
        check_playwright_ids,
    ),
    Check(
        "play-ids",
        "Play ids shared by two titles",
        "Two spellings of a title make one id, which the play index then lists "
        "twice. Title the play the same way in every show.",
        Severity.DEFECT,
        check_play_ids,
    ),
]


def get_credited_person_ids() -> set[str]:
    return {
        row.person_id
        for row in database.PersonRole.select(database.PersonRole.person_id).where(
            database.PersonRole.person_id.is_null(False)
        )
    }


def get_person_document_ids() -> set[str]:
    return {person.id for person in database.Person.select(database.Person.id)}


def check_person_name_collisions() -> list[Finding]:
    """
    Two names behind one id, with no document to settle which is canonical.

    Crediting someone under a variant name is normal, and a `_people/` document
    fixes the name the API dumps. Without one the name comes from whichever credit
    the query happens to reach first.
    """
    names: dict[str, set[str]] = defaultdict(set)
    for row in database.PersonRole.select().where(
        database.PersonRole.person_id.is_null(False),
        database.PersonRole.person_name.is_null(False),
    ):
        names[row.person_id].add(row.person_name)
    documented = get_person_document_ids()
    return [
        Finding(person_id, hint="credited as " + ", ".join(sorted(person_names)))
        for person_id, person_names in sorted(names.items())
        if len(person_names) > 1 and person_id not in documented
    ]


def check_committee_roles() -> list[Finding]:
    """A committee credit without a role appears in no role index."""
    return [
        Finding(
            str(row.role),
            hint=f"{row.person_name} on the {row.target_id} committee",
        )
        for row in database.PersonRole.select().where(
            database.PersonRole.target_type == database.PersonRoleType.COMMITTEE
        )
        if row.role is None or row.role in roles.UNKNOWN_ROLE_NAMES
    ]


def check_trivia_people() -> list[Finding]:
    """Trivia from someone with neither credits nor a document is never dumped."""
    known = get_credited_person_ids() | get_person_document_ids()
    return [
        Finding(str(row.person_name), hint=f"trivia on {row.target_id}")
        for row in database.Trivia.select().where(
            database.Trivia.person_id.is_null(False)
        )
        if row.person_id not in known
    ]


def check_awards_known() -> list[Finding]:
    """An award beyond the known set appears on the person, but on no year list."""
    known_awards = {award.value for award in models.Award}
    return [
        Finding(
            str(model.award),
            person_inst.source_path,
            "outside the known set, so it is on no year page",
        )
        for person_inst, model in get_person_models()
        if model.award is not None and model.award not in known_awards
    ]


def get_years_active() -> dict[str, list[int]]:
    years_active: dict[str, list[int]] = defaultdict(list)
    for row in database.PersonRole.select().where(
        database.PersonRole.person_id.is_null(False)
    ):
        years_active[row.person_id].append(row.target_year)
    return years_active


def check_graduation_plausible() -> list[Finding]:
    """A graduation year far from someone's credits reads as a typo."""
    years_active = get_years_active()
    findings = []
    for person_inst, model in get_person_models():
        years = years_active.get(person_inst.id)
        if model.graduated is None or not years:
            continue
        if model.graduated < min(years):
            findings.append(
                Finding(
                    str(model.graduated),
                    person_inst.source_path,
                    f"before their first credit in {min(years)}",
                )
            )
        elif model.graduated > max(years) + MAX_YEARS_AFTER_LAST_CREDIT:
            findings.append(
                Finding(
                    str(model.graduated),
                    person_inst.source_path,
                    f"over {MAX_YEARS_AFTER_LAST_CREDIT} years after their last "
                    f"credit in {max(years)}",
                )
            )
    return findings


def get_active_year_clusters(years: Iterable[int]) -> list[list[int]]:
    """Active years split wherever the break between them is long enough."""
    clusters: list[list[int]] = []
    for year in sorted(set(years)):
        if clusters and year - clusters[-1][-1] < MERGE_GAP_YEARS:
            clusters[-1].append(year)
        else:
            clusters.append([year])
    return clusters


def format_year_clusters(clusters: list[list[int]]) -> str:
    spans = [
        str(cluster[0]) if cluster[0] == cluster[-1] else f"{cluster[0]}-{cluster[-1]}"
        for cluster in clusters
    ]
    *earlier, last = spans
    return " and ".join([", ".join(earlier), last]) if earlier else last


class PersonDocument(NamedTuple):
    source_path: str
    graduated: int | None


def get_person_documents() -> dict[str, PersonDocument]:
    return {
        person.id: PersonDocument(person.source_path, person.graduated)
        for person in database.Person.select()
    }


def clusters_fit_graduation(clusters: list[list[int]], graduated: int) -> bool:
    """Whether every cluster falls in the working life a graduation year implies."""
    return all(
        abs(year - graduated) <= DOCUMENTED_GRADUATION_MARGIN
        for cluster in clusters
        for year in (cluster[0], cluster[-1])
    )


class MergedPeople(NamedTuple):
    findings: list[Finding]
    skipped: list[str]


def find_merged_people() -> MergedPeople:
    """
    Ids whose credits fall in clusters far enough apart to be two careers.

    A documented person is taken as read where their `graduated` year vouches
    for the whole span; without one, a document is no answer to the gap.
    """
    documents = get_person_documents()
    findings: list[Finding] = []
    skipped: list[str] = []
    for person_id, years in sorted(get_years_active().items()):
        clusters = get_active_year_clusters(years)
        if len(clusters) <= 1:
            continue
        spans = format_year_clusters(clusters)
        document = documents.get(person_id)
        if (
            document is not None
            and document.graduated is not None
            and clusters_fit_graduation(clusters, document.graduated)
        ):
            skipped.append(f"{person_id}: {spans}, graduated {document.graduated}")
            continue
        findings.append(
            Finding(
                person_id,
                document.source_path if document else None,
                f"{spans} ({pluralise(len(years), 'credit')})",
            )
        )
    return MergedPeople(findings, skipped)


def check_merged_people() -> list[Finding]:
    return find_merged_people().findings


def describe_skipped_merged_people() -> str | None:
    skipped = find_merged_people().skipped
    if not skipped:
        return None
    people_or_person = "person" if len(skipped) == 1 else "people"
    return (
        f"Skipped {len(skipped)} documented {people_or_person}, "
        f"vouched for by their graduation year: " + "; ".join(skipped)
    )


def check_tour_dates() -> list[Finding]:
    """A tour date with neither a venue nor a date says nothing."""
    return [
        Finding(
            f"tour date {index + 1}",
            show_inst.source_path,
            "neither a venue nor a date",
        )
        for show_inst, model in get_show_models()
        for index, tour_date in enumerate(model.tour)
        if tour_date.venue is None
        and tour_date.date_start is None
        and tour_date.date_end is None
    ]


def check_person_refs_named() -> list[Finding]:
    """A credit without a name dumps a role with nobody in it."""
    return [
        Finding(str(row.role), hint=f"credited on {row.target_id}")
        for row in database.PersonRole.select().where(
            database.PersonRole.person_name.is_null(True)
        )
    ]


def check_asset_categories() -> list[Finding]:
    """An image of an unknown category cannot be picked as a show's poster."""
    known_categories = {category.value for category in assets.AssetCategory}
    counts: dict[str, int] = defaultdict(int)
    for row in database.Asset.select().where(
        database.Asset.asset_category.is_null(False),
        database.Asset.asset_type == str(assets.AssetType.IMAGE),
    ):
        if row.asset_category not in known_categories:
            counts[row.asset_category] += 1
    return [
        Finding(category, hint=pluralise(count, "image"))
        for category, count in sorted(counts.items())
    ]


def check_venue_sort() -> list[Finding]:
    """`venue_sort` groups a venue, so without a venue it does nothing."""
    return [
        Finding(
            str(show_inst.venue_sort), show_inst.source_path, "the show has no venue"
        )
        for show_inst in database.Show.select().where(
            database.Show.venue_sort.is_null(False),
            database.Show.venue_id.is_null(True),
        )
    ]


def get_person_id_parts(person_id: str) -> tuple[str, str]:
    forename, _, remainder = person_id.partition("_")
    return forename, remainder


def check_forenames_are_alike(first: str, second: str) -> bool:
    """
    Whether two forenames read as one person written two ways.

    They have to open the same way — a shared surname alone puts far too many
    people together — and then be alike enough over the whole name, which is what
    catches a short form such as `joe` against `joseph`.
    """
    if first[:FORENAME_SHARED_PREFIX] != second[:FORENAME_SHARED_PREFIX]:
        return False
    if first == second:
        return False
    return SequenceMatcher(None, first, second).ratio() >= FORENAME_SIMILARITY_LIMIT


def check_near_duplicate_person_ids() -> list[Finding]:
    """
    Ids sharing a surname whose forenames are near enough to be one person, such
    as `joe_bloggs` and `joseph_bloggs`.

    Two such ids are two people as far as the API is concerned, so one person's
    credits are split between them.
    """
    ids_by_surname: dict[str, list[str]] = defaultdict(list)
    for person_id in sorted(get_credited_person_ids() | get_person_document_ids()):
        forename, surname = get_person_id_parts(person_id)
        if forename and surname:
            ids_by_surname[surname].append(person_id)
    return [
        Finding(f"{first} / {second}", hint="may be one person, credits split in two")
        for person_ids in ids_by_surname.values()
        for index, first in enumerate(person_ids)
        for second in person_ids[index + 1 :]
        if check_forenames_are_alike(
            get_person_id_parts(first)[0], get_person_id_parts(second)[0]
        )
    ]


def check_show_seasons() -> list[Finding]:
    """A show whose season matched no definition is in no season index."""
    return [
        Finding(model.season, show_inst.source_path, "matches no known season")
        for show_inst, model in get_show_models()
        if show_inst.season_id is None
    ]


def check_venue_documents() -> list[Finding]:
    """Most venues are referenced by shows alone; those are dumped as stubs."""
    documented = {venue.id for venue in database.Venue.select(database.Venue.id)}
    referenced: dict[str, int] = defaultdict(int)
    for show in database.Show.select().where(database.Show.venue_id.is_null(False)):
        referenced[show.venue_id] += 1
    return [
        Finding(venue_id, hint=f"{pluralise(count, 'show')}, dumped as a stub")
        for venue_id, count in sorted(referenced.items())
        if venue_id not in documented and venue_id not in SENTINEL_VENUE_IDS
    ]


def check_crew_role_definitions() -> list[Finding]:
    """A crew role beyond `_data/roles.yaml` gets no role index of its own."""
    return [
        Finding(role_name, hint="no definition in _data/roles.yaml")
        for role_name in roles.get_crew_roles_without_definition()
    ]


def check_link_type_definitions() -> list[Finding]:
    """A link type beyond `_data/link-types.yaml` keeps its authored name."""
    counts: dict[str, int] = defaultdict(int)
    for _, model in get_person_models():
        for link in [*model.links, *model.news]:
            if links.get_link_type_definition(link.type) is None:
                counts[link.type] += 1
    for _, show_model in get_show_models():
        for link in show_model.links:
            if links.get_link_type_definition(link.type) is None:
                counts[link.type] += 1
    return [
        Finding(link_type, hint=pluralise(count, "link"))
        for link_type, count in sorted(counts.items())
    ]


def check_placeholder_content() -> list[Finding]:
    """A body that is only an HTML comment renders to nothing at all."""
    return get_recorded_findings(PLACEHOLDER_CONTENT_CHECK)


def check_scalar_list_fields() -> list[Finding]:
    """`course` and `careers` take a list; a bare value is read as a list of one."""
    return get_recorded_findings(SCALAR_LIST_FIELD_CHECK)


LINT_CHECKS: list[Check] = [
    Check(
        "person-names",
        "People credited under two names",
        "One id, two spellings, and no `_people/` document to say which name is "
        "right, so the name shown is whichever the API reads first. Add a document "
        "for them, or spell the name the same way in every credit.",
        Severity.WORTH_FIXING,
        check_person_name_collisions,
    ),
    Check(
        "duplicate-people",
        "People who may be one person twice",
        "Two ids alike enough to be one person written two ways, which splits "
        "their credits between two pages. Where they are the same person, use one "
        "spelling, or set `id` on the person to join them up.",
        Severity.WORTH_FIXING,
        check_near_duplicate_person_ids,
    ),
    Check(
        "merged-people",
        "People whose credits span two eras",
        "Credits decades apart under one id — probably two people with the same "
        "name. If they are one person add a `_people/` document; if two, set `id` "
        "on the later credits.",
        Severity.WORTH_FIXING,
        check_merged_people,
        describe_skipped_merged_people,
    ),
    Check(
        "unnamed-credits",
        "Credits with no name",
        "A cast or crew entry with a role and no `name`, dumped as a role with "
        "nobody in it. Add the name, or remove the entry.",
        Severity.WORTH_FIXING,
        check_person_refs_named,
    ),
    Check(
        "committee-roles",
        "Committee credits with no role",
        "A committee member with no role, or `unknown`, appears on no role page. "
        "Name the position they held.",
        Severity.WORTH_FIXING,
        check_committee_roles,
    ),
    Check(
        "trivia-people",
        "Trivia from people the archive does not know",
        "The person named has no credits and no document, so the trivia is dumped "
        "without them. Check the spelling of the name.",
        Severity.WORTH_FIXING,
        check_trivia_people,
    ),
    Check(
        "awards",
        "Awards outside the known set",
        "The award shows on the person's page but on no year page. Use one of "
        "Fellowship, Commendation, Merit or Union Prize.",
        Severity.WORTH_FIXING,
        check_awards_known,
    ),
    Check(
        "graduation",
        "Graduation years that look wrong",
        "The year is before their first credit, or long after their last, which "
        "usually means a typo. Check it against their shows.",
        Severity.WORTH_FIXING,
        check_graduation_plausible,
    ),
    Check(
        "tour-dates",
        "Tour dates with nothing in them",
        "A tour entry with neither a venue nor a date says nothing. Fill it in or "
        "take it out.",
        Severity.WORTH_FIXING,
        check_tour_dates,
    ),
    Check(
        PLACEHOLDER_CONTENT_CHECK,
        "Bodies that are only a comment",
        "The body below the frontmatter is an HTML comment, so the page shows "
        "nothing. Write it, or leave the file without a body.",
        Severity.WORTH_FIXING,
        check_placeholder_content,
    ),
    Check(
        "venue-sort",
        "Venue grouping without a venue",
        "`venue_sort` groups a show under its venue, so without `venue` it does "
        "nothing. Add the venue.",
        Severity.WORTH_FIXING,
        check_venue_sort,
    ),
    Check(
        "show-seasons",
        "Shows in no known season",
        "The season matches none the site knows, so the show is in no season "
        "index. Use one of the established season names.",
        Severity.WORTH_FIXING,
        check_show_seasons,
    ),
    Check(
        SCALAR_LIST_FIELD_CHECK,
        "Fields authored as a bare value",
        "`course` and `careers` are lists. A bare value still works, read as a "
        "list of one, but a list is the house style.",
        Severity.ADVISORY,
        check_scalar_list_fields,
    ),
    Check(
        "venue-documents",
        "Venues with no document",
        "Most venues are named by shows alone and are dumped as stubs: a name and "
        "the shows there. Add a `_venues/` file to give one a description.",
        Severity.ADVISORY,
        check_venue_documents,
    ),
    Check(
        "crew-roles",
        "Crew roles with no definition",
        "The role is credited as authored, but gets no role page of its own. Add "
        "it to `_data/roles.yaml`, as itself or as an alias of a role there.",
        Severity.ADVISORY,
        check_crew_role_definitions,
    ),
    Check(
        "link-types",
        "Link types with no definition",
        "The link works and keeps its authored type, but gets no icon or news "
        "handling. Add it to `_data/link-types.yaml` if it is worth one.",
        Severity.ADVISORY,
        check_link_type_definitions,
    ),
    Check(
        "image-categories",
        "Images in no category",
        "Only posters, flyers, programmes and headshots are categorised; anything "
        "else cannot be picked as a show's main image.",
        Severity.ADVISORY,
        check_asset_categories,
    ),
]

CHECKS_BY_NAME = {check.name: check for check in [*BUILD_CHECKS, *LINT_CHECKS]}
LINT_CHECK_NAMES = [check.name for check in LINT_CHECKS]


def run_checks(checks: Iterable[Check]) -> dict[Check, list[Finding]]:
    return {check: check.func() for check in checks}


def run_build_checks() -> int:
    """Report cross-document defects as ERRORs; returns how many were found."""
    results = run_checks(BUILD_CHECKS)
    for check, findings in results.items():
        for finding in findings:
            log.error(f"{check.name}: {finding}")
    total = sum(len(findings) for findings in results.values())
    log.info(f"Validation found {total} cross-document defects")
    return total


def run_lint_checks(names: Iterable[str] | None = None) -> dict[Check, list[Finding]]:
    """Every lint check, reported rather than alarmed: findings are expected."""
    if names is None:
        return run_checks(LINT_CHECKS)
    return run_checks([CHECKS_BY_NAME[name] for name in names])
