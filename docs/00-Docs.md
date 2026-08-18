---
type: reference
---

# About these docs

Start here. This folder is the working documentation for nthp-api: reviews, plans and task write-ups, numbered in creation order.

Conventions (shared with `~/local/lumina/docs`):

- Filenames are `NN-Title.md`; numbers never reused or reordered.
- Frontmatter `type`: `reference` (evergreen), `review` (point-in-time assessment, has `status: open|done`), `task` (a unit of work, has `status`).
- Reviews are snapshots — they state their date and the commit they assessed; they are not updated to track the code. Tasks and the plan are living documents.

Reading order:

1. [01-Project plan](01-Project%20plan.md) — where the project is going; implements the reviews' recommendations
2. [02-Project review](02-Project%20review.md) — speed, reliability, structural bugs, unattended operation
3. [03-Completeness review](03-Completeness%20review.md) — coverage vs the Ruby/Jekyll builder this replaces
4. [04-Strictness review](04-Strictness%20review.md) — what validation should tighten and loosen
