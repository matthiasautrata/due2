# Archive

This directory keeps documents that are no longer current, for the record of how due2 got where it is. Nothing here is normative. Where an archived document and a current one disagree, the current one holds. Git has the full history. The archive is for a reader who wants the story without running `git log`.

| File | What it was | Current until | Replaced by |
|---|---|---|---|
| `implementation-alternatives.md` | The review of how to build and verify W1: Python with a Dafny oracle, Lean, Clingo, and OCaml with Why3. | 2026-10-10 | Its outcome is `decisions/0002`. `decisions/0009` replaced the review's Python direct interpreter with a clingo program, and `decisions/0006` reopened the W2/W3 backend as a bakeoff. |
| `implementation-alternatives-ii.md` | A comparison of host platforms for due2: the standing Python path, and Elixir on the BEAM with Rust for the hot path. It includes a decision rule and the triggers that would flip it. | 2026-10-16 | `decisions/0006`, the W2/W3 bakeoff, which enters Elixir as a backend under the conformance suite. |
| `changes.md` | The **Changes** entries that each specification and design document carried before its latest one, and README's Status paragraph as it stood on 2026-10-19. | Each entry: until its document's next version | Each document's latest **Changes** line, and README § Status |
