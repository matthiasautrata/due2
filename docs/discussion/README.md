# Discussion

Proposals that are not yet settled. A briefing records what is, at a commit; a decision record states what was decided. A discussion document holds what is being decided: one question, the argument for an answer, the alternatives rejected, and the exact edits acceptance would force, file by file, with the issues it closes or opens. Accepting one is therefore a review, not a rewrite.

Nothing here is normative. Where a discussion document and a specification disagree, the specification holds, and the disagreement is the reason the document exists.

**Lifecycle.** A document here is written before its edits land. When the owner accepts it, the decision record is written from it and the edits land in the increment it schedules; the document then stays here while its steps are open, and moves to `docs/archive/` with an index row when the last step closes. A document that is dropped moves to `docs/archive/` with the reason it was dropped, because a rejected alternative is worth more than its absence.

| File | Question | Status |
|---|---|---|
| `evaluator-boundary.md` | What an id is, what a document is, and what crosses between two published components: minted ids, no derived id, JSON-LD as the only wire form | Proposed, 2026-10-30, for review; the plan for #172 |
