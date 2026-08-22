---
type: task
status: todo
---

# Roles

Web doc 30 §2, 03 §Role definitions. `roles.py` hardcodes 11 crew + 2 committee roles; content has 77 distinct committee role strings and `_data/roles.yaml` defines 31 crew roles with aliases.

## Output

- `GET /roles/committee/index.json` → `Role[]` (new) — `{id, role, aliases[], count}`
- `GET /roles/committee/{id}.json` for **every** role, not 2
- `GET /roles/crew/index.json` gains `count`; crew roles come from `roles.yaml`

## Do

- Committee: role set from `SELECT DISTINCT role WHERE target_type = COMMITTEE`; `COMMITTEE_ROLE_DEFINITIONS` becomes a curated alias map layered on top. Exclude `unknown`/`Unknown`. Id: `slugify(role, separator="_")` as today.
- Seed aliases: `Marketing Co-ordinator`/`Marketing Coordinator`, `Costume, Props and Make-Up Manager`/`…Make-up Manager`, `Committee Member(s)`, `Production Manager`/`Productions Manager`. Audit the full 77 for more.
- Crew: delete `CREW_ROLE_DEFINITIONS`; load `_data/roles.yaml` from the content repo at load time (icons ignored — presentation). Strip the trailing whitespace roles.yaml values carry. Note roles.yaml maps Author/Writer/Adaptor/Translator → Playwright; interacts with `playwright_alias` (16).
- `count` on `Role` = number of holdings.
- `nthp lint` style warning for roles matching no definition.

