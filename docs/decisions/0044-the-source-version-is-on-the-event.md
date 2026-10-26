# 0044 — The source version is recorded on the event

**Status:** Decided, 2026-10-26 (the owner, in the review of `due2-platform.md` on that date)
**Context documents:** `due2-workflows.md` §3.3, §7.1 · `due2-architecture.md` §7 · `decisions/0040` · `decisions/0043`

## Question

`due2-workflows.md` v0.50 §3.3, *Answers, not extensions*, says that when a source answers from bulk data, the shell records the answer "and the version of the source it came from". No relation of the SOTW or the ledger has a field for it, and none had one before `decisions/0040` either: the `attribution` it dropped held only `observed_at`. Where is the version recorded?

## Decision

1. **An event carries the version of the source that answered.** `event (case_id, seq | kind, valid_at?, source_version?, ref)`. The shell fills it for a `fact` or `closure` event (`decisions/0043`) when the source reports a version, and leaves it absent otherwise.
2. **W2 never reads it.** The version is not part of the SOTW, so it changes no trace and no SOTW digest.

## Why this holds

- **The version is about where the answer came from, not what it says.** Two sources at different versions that give the same answer give the part the same truth value. The version explains an answer to an auditor, as `valid_at` dates it, so it belongs beside `valid_at` on the event.
- **A field W2 reads would have to be in the SOTW, and nothing would use it there.** No rule of `due2-workflows.md` §5 or §6 depends on a source's version.

## Rejected

- **The version in the source's IRI.** A new version would then be a new source, so `fact (property, source)` would hold a fresh key for each version, and the answer of the old version would not be replaced by the new one's (`decisions/0040` #2).
- **The version on the SOTW `fact`.** It would enter the SOTW digest, so two SOTWs with the same answers would differ in id.

## Consequences

- `due2-workflows.md` v0.51: §7.1 adds the field, and §3.3 *Answers, not extensions* cites it.
- `due2-platform.md` v0.13: `resolve` and `edges` return the source's version with each answer (§2.4).
