---
type: task
status: todo
---

# Trivia embedding

Web doc 30 §5. Embed `trivia: TriviaItem[]` on `ShowDetail` and `PersonDetail`; remove `/trivia/shows/{id}.json` and `/trivia/people/{id}.json` (dumpers, spec, tests). ~120 items total; no second fetch, no 404-vs-empty ambiguity.

Source: `database.Trivia`, grouping already in `dump_targeted_trivia` / `dump_people_trivia` — move, don't rewrite.
