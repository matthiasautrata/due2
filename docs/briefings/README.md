# Briefings

A briefing is a dated snapshot of due2 for readers who have not followed its design: what it does, what its checks establish, and what remains. Each one states the commit it describes, and its numbers and examples come from that commit.

Briefings are not maintained. A briefing may be revised on the day of its date, and its row below then says so. When the repository moves on, a briefing stays as it was, and a later one supersedes it. For the current state, read `README.md` § Status and the issues; for the semantics, read the documents under `docs/spec/`. A briefing's recommendations are suggestions until an issue or a decision record adopts them.

The directory also keeps reviews of due2 by an outside reader. A review is kept as received, except for the changes its own note lists, and it is not revised. Its findings are inputs: each one is verified before an issue or a decision record takes it up.

| Briefing | Commit | Scope |
|---|---|---|
| `due2-briefing-2026-10-21.md` | `ce17910` | The whole project, and a primer on reading test numbers: oracles, the rule of three, planted bugs, generator strength |
| `due2-briefing-2026-10-24.md` | `c711e89` | Supersedes 10-21: the bounded-exhaustive spaces, the Alloy models of the formal claims, the listed frontier of `decisions/0026`, and decisions 0022 to 0026. §8 was revised the same day for `decisions/0021`'s amendment and `decisions/0027`. |
| `due2-review-2026-10-24.md` | `dc232b5` | An external correctness and oracle-readiness review: fifteen findings (R01–R15) on the semantic contract, admission, the ODRL validation layer, the laws, and the qualification of clingo-i, with four gates in recommended order |
| `due2-review-2026-10-25.md` | `beb7c5f` | A follow-up review after the first review's findings were settled: their disposition, and seven new findings (F01–F07) on trace and instance identity, refined and inverse ODRL forms, temporal lexical checks, profile-defined parties, and constraint cycles, with four gates in recommended order |
