---
type: task
status: done
---

# Honourifics

Some people pick up a style or an honour after leaving the theatre — Sir, Dame,
Professor, OBE, FRS. The archive had nowhere to record them: `award` is the
theatre's own leaving award (Fellowship, Commendation) and `title` has to stay
the bare name, as the person id is slugified from it.

## Content

Two authored fields on `models.Person`, both free text and held to no list:

- `pre_nominal: str | None` — one style, as it should read before the name.
- `post_nominals: list[str]` — honours in the order they should read.

Both are described as separate from `award`, and as not touching `title`. They
reach the published content schema, the schema page and `nthp new person` for
free, all being generated from the model.

## API

`PersonDetail` only, as `preNominal` and `postNominals`. Not on
`PersonIndexItem`, `PersonRef` or the search documents: a list entry is a name
and an id, and the search index matches on the bare name.

Nothing is combined into a display string — the front end decides whether a
listing reads "Fred Bloggs" and a page reads "Sir Fred Bloggs OBE".

## Notes

Absent honourifics dump as an omitted `preNominal` and an empty `postNominals`,
per the `write_file` rule: null scalars are omitted, lists always written.
