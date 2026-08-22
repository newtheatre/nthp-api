"""
Checks over the loaded database, once every document is in it.

Cross-document defects — two spellings of one venue, two names behind one id —
cannot be seen while a single document is loading, so they are checked here,
between the loaders and the dump.

Build checks report defects that should be fixed, as ERRORs naming the documents
at fault. Lint checks report the expected and the advisory, and are reported by
`nthp lint` rather than alarming a build.
"""

import json
import logging
import re
from collections import defaultdict
from difflib import SequenceMatcher
from collections.abc import Callable, Iterable
from typing import NamedTuple

from nthp_api.nthp_build import assets, database, links, models, people, roles

log = logging.getLogger(__name__)

MAX_YEARS_AFTER_LAST_CREDIT = 10
# How alike two forenames behind one surname must be to read as one person.
FORENAME_SIMILARITY_LIMIT = 0.6
FORENAME_SHARED_PREFIX = 2


class Finding(NamedTuple):
    """One thing a check found, with the document it belongs to if there is one."""

    message: str
    source_path: str | None = None

    def __str__(self) -> str:
        return f"{self.source_path}: {self.message}" if self.source_path else self.message


class Check(NamedTuple):
    name: str
    func: Callable[[], list[Finding]]


PLACEHOLDER_CONTENT_CHECK = "placeholder content"
SCALAR_LIST_FIELD_CHECK = "scalar list fields"

PLACEHOLDER_CONTENT_PATTERN = re.compile(r"^\s*(<!--.*?-->\s*)+$", re.DOTALL)


def record_finding(check: str, message: str, source_path: str) -> None:
    """
    Note something only the loader can see, for `nthp lint` to report later.

    The authored shape of a document is gone by the time it reaches sqlite: a
    coerced value and a placeholder body both look ordinary from there.
    """
    database.LoadFinding.create(check=check, message=message, source_path=source_path)


def get_recorded_findings(check: str) -> list[Finding]:
    return [
        Finding(row.message, row.source_path)
        for row in database.LoadFinding.select()
        .where(database.LoadFinding.check == check)
        .order_by(database.LoadFinding.source_path)
    ]


def check_content_is_not_a_placeholder(content: str, source_path: str) -> None:
    if content.strip() and PLACEHOLDER_CONTENT_PATTERN.match(content):
        record_finding(
            PLACEHOLDER_CONTENT_CHECK,
            "body is only an HTML comment, so it renders to nothing",
            source_path,
        )


def get_person_models() -> Iterable[tuple[database.Person, models.Person]]:
    for person_inst in database.Person.select():
        yield person_inst, models.Person(**json.loads(person_inst.data))


def get_show_models() -> Iterable[tuple[database.Show, models.Show]]:
    for show_inst in database.Show.select():
        yield show_inst, models.Show(**json.loads(show_inst.data))


def check_venue_spellings() -> list[Finding]:
    """A venue id authored under several spellings takes the commonest, arbitrarily."""
    spellings: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for show in database.Show.select().where(
        database.Show.venue_id.is_null(False),
        database.Show.venue_name.is_null(False),
    ):
        spellings[show.venue_id][show.venue_name].append(show.source_path)
    return [
        Finding(
            f"venue {venue_id!r} is authored as "
            + "; ".join(
                f"{name!r} in {sorted(paths)[0]} and {len(paths) - 1} more"
                if len(paths) > 1
                else f"{name!r} in {paths[0]}"
                for name, paths in sorted(names.items())
            )
        )
        for venue_id, names in sorted(spellings.items())
        if len(names) > 1
    ]


def check_award_graduation() -> list[Finding]:
    """An award is filed under the year its holder graduated, so it needs one."""
    return [
        Finding(
            f"holds the award {model.award!r} but has no known or estimable "
            f"graduation year, so it appears on no year",
            person_inst.source_path,
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


def check_playwright_ids() -> list[Finding]:
    """Two spellings of a writer's name collide as one id, dumped twice over."""
    return [
        Finding(
            f"playwright id {playwright_id!r} is shared by "
            f"{', '.join(f'{name!r} ({shows[0]})' for name, shows in sorted(names.items()))}"
        )
        for playwright_id, names in sorted(
            _duplicate_names_by_id("playwright_id", "playwright_name").items()
        )
    ]


def check_play_ids() -> list[Finding]:
    """Two spellings of a play's title collide as one id, dumped twice over."""
    return [
        Finding(
            f"play id {play_id!r} is shared by "
            f"{', '.join(f'{name!r} ({shows[0]})' for name, shows in sorted(names.items()))}"
        )
        for play_id, names in sorted(_duplicate_names_by_id("play_id", "play_name").items())
    ]


BUILD_CHECKS: list[Check] = [
    Check("venue spellings", check_venue_spellings),
    Check("award graduation", check_award_graduation),
    Check("playwright ids", check_playwright_ids),
    Check("play ids", check_play_ids),
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
        Finding(
            f"person id {person_id!r} is credited as "
            f"{', '.join(sorted(person_names))}, with no document to settle the name"
        )
        for person_id, person_names in sorted(names.items())
        if len(person_names) > 1 and person_id not in documented
    ]


def check_committee_roles() -> list[Finding]:
    """A committee credit without a role appears in no role index."""
    return [
        Finding(
            f"committee credit for {row.person_name!r} in {row.target_id} has "
            f"role {row.role!r}, so it appears in no role index"
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
        Finding(
            f"trivia on {row.target_id} names {row.person_name!r}, who has no "
            f"credits and no document, so the attribution is never dumped"
        )
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
            f"holds the award {model.award!r}, which is outside the known set, so "
            f"it appears on no year list",
            person_inst.source_path,
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
                    f"graduated in {model.graduated}, before their first credit in "
                    f"{min(years)}",
                    person_inst.source_path,
                )
            )
        elif model.graduated > max(years) + MAX_YEARS_AFTER_LAST_CREDIT:
            findings.append(
                Finding(
                    f"graduated in {model.graduated}, over "
                    f"{MAX_YEARS_AFTER_LAST_CREDIT} years after their last credit "
                    f"in {max(years)}",
                    person_inst.source_path,
                )
            )
    return findings


def check_tour_dates() -> list[Finding]:
    """A tour date with neither a venue nor a date says nothing."""
    return [
        Finding(
            f"tour date {index + 1} has neither a venue nor a date",
            show_inst.source_path,
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
        Finding(
            f"credit for role {row.role!r} on {row.target_id} has no name, so the "
            f"role is dumped with nobody in it"
        )
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
        Finding(f"image type {category!r} matches no category ({count} images)")
        for category, count in sorted(counts.items())
    ]


def check_venue_sort() -> list[Finding]:
    """`venue_sort` groups a venue, so without a venue it does nothing."""
    return [
        Finding("has a venue_sort but no venue", show_inst.source_path)
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
        Finding(f"person ids {first!r} and {second!r} may be the same person")
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
        Finding("has no recognised season", show_inst.source_path)
        for show_inst in database.Show.select().where(
            database.Show.season_id.is_null(True)
        )
    ]


def check_venue_documents() -> list[Finding]:
    """Most venues are referenced by shows alone; those are dumped as stubs."""
    documented = {venue.id for venue in database.Venue.select(database.Venue.id)}
    referenced: dict[str, int] = defaultdict(int)
    for show in database.Show.select().where(database.Show.venue_id.is_null(False)):
        referenced[show.venue_id] += 1
    return [
        Finding(f"venue {venue_id!r} has no document ({count} shows)")
        for venue_id, count in sorted(referenced.items())
        if venue_id not in documented and venue_id not in {"unknown", "youtube"}
    ]


def check_crew_role_definitions() -> list[Finding]:
    """A crew role beyond `_data/roles.yaml` gets no role index of its own."""
    return [
        Finding(f"crew role {role_name!r} matches no definition in roles.yaml")
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
        Finding(f"link type {link_type!r} matches no definition ({count} links)")
        for link_type, count in sorted(counts.items())
    ]


def check_placeholder_content() -> list[Finding]:
    """A body that is only an HTML comment renders to nothing at all."""
    return get_recorded_findings(PLACEHOLDER_CONTENT_CHECK)


def check_scalar_list_fields() -> list[Finding]:
    """`course` and `careers` take a list; a bare value is read as a list of one."""
    return get_recorded_findings(SCALAR_LIST_FIELD_CHECK)


LINT_CHECKS: list[Check] = [
    Check("person name collisions", check_person_name_collisions),
    Check(PLACEHOLDER_CONTENT_CHECK, check_placeholder_content),
    Check(SCALAR_LIST_FIELD_CHECK, check_scalar_list_fields),
    Check("committee roles", check_committee_roles),
    Check("trivia people", check_trivia_people),
    Check("awards", check_awards_known),
    Check("graduation plausibility", check_graduation_plausible),
    Check("tour dates", check_tour_dates),
    Check("credits without a name", check_person_refs_named),
    Check("image categories", check_asset_categories),
    Check("venue sort", check_venue_sort),
    Check("near-duplicate person ids", check_near_duplicate_person_ids),
    Check("show seasons", check_show_seasons),
    Check("venues without a document", check_venue_documents),
    Check("crew role definitions", check_crew_role_definitions),
    Check("link type definitions", check_link_type_definitions),
]


def run_checks(checks: list[Check]) -> dict[str, list[Finding]]:
    return {check.name: check.func() for check in checks}


def run_build_checks() -> int:
    """Report cross-document defects as ERRORs; returns how many were found."""
    results = run_checks(BUILD_CHECKS)
    for check_name, findings in results.items():
        for finding in findings:
            log.error(f"{check_name}: {finding}")
    total = sum(len(findings) for findings in results.values())
    log.info(f"Validation found {total} cross-document defects")
    return total


def run_lint_checks() -> dict[str, list[Finding]]:
    """Every lint check, reported rather than alarmed: findings are expected."""
    return run_checks(LINT_CHECKS)


def format_lint_report(results: dict[str, list[Finding]], examples: int) -> str:
    """A count per check, with the first few findings under each."""
    lines = []
    for check_name, findings in results.items():
        lines.append(f"{len(findings):5d}  {check_name}")
        lines.extend(f"        {finding}" for finding in findings[:examples])
        if len(findings) > examples:
            lines.append(f"        ... and {len(findings) - examples} more")
    lines.append(f"{sum(len(findings) for findings in results.values()):5d}  total")
    return "\n".join(lines)
