# 0009 — The semantics live in a Clingo program; Python builds no evaluator

**Status:** Decided, 2026-10-16
**Supersedes:** `decisions/0002` #1 and #7 as written (Python for W2/W3 and as the L9 oracle) and the Python W2/W3 backend of `decisions/0006` (issue #39). `decisions/0002` #5's exclusion is reversed for the spec/oracle role, not for the runtime.
**Context documents:** `decisions/0002` · `decisions/0006` · `due2-workflows.md` §5–§6, §6.4 · `correctness-strategy.md` §1.1, §3–§5, §8 · `implementation-alternatives.md` §5 (the 2026-10-10 clingo audit) · `ways-of-working.md` §2.4, §5.1 · issues #9, #36–#42

## Question

The evaluator, its oracle, and the generators were all to be Python (0002, correctness-strategy). The owner rules that out — no ODRL parser/eval machine in Python. Can the semantics be authored once, declaratively, and serve as corpus runner, bakeoff candidate, and test generator, with the semantics and laws unchanged?

## Decision

1. **The ODRL evaluation semantics are authored once, as a generic ASP program (clingo) over flattened ODRL.** Python builds no evaluator: no W2/W3 implementation, no direct interpreter. Workflows §1–§8, the relations, and L1–L9 are unchanged — this changes vehicles, not semantics.
2. **Stage A — relation-level vectors.** Input is the relations of workflows §3.1–§3.4 as facts (JCS collections, `decisions/0007`; the vector format is #36); output is the five verdicts with the frontier. The Python driver flattens corpus cases and policies into facts and owns digests, canonical bytes, and id minting — the functional parts the 2026-10-10 audit named as alien to a logic engine. RDF stays at the boundary (`ways-of-working.md` §2.4).
3. **Stage B — the whole grammar, built first.** The shared suite's first task is `interpret` (`spikes/README.md`), and its vectors are the corpus itself, so the first spike builds Stage B: the driver makes a purely syntactic flatten — authored graph to facts; no expansion, no DNF, which are the program's rules — and the structural rules (interiorisation, expansion, DNF) are declarative rules from the start. The program is then the direct interpreter over the authored form, and L9 is the differential between its run and the atomised pipeline, once W1 exists. Stage A's relation-level vectors follow for the bakeoff (#36).
4. **Encoding obligations — the gate the audit failed.** `U` is data, never negation-as-failure: fact statuses (`resolved/missing/invalid/conflict/unresolved`), deadline comparisons (§5.3: a fact of the SOTW), and witness timeliness arrive as facts. Every part carries exactly one of `t/f/u`, enforced by an integrity constraint from day one — a forgotten rule is a loud failure, not a silent false. Kleene conjunction and disjunction are min/max over `f < u < t`; `dprod:not` is the involution.
5. **Completion is answer-set enumeration.** One choice rule per unknown literal yields one answer set per completion; a verdict is definite iff cautious-entailed (`--cautious`). The caps (`max_mixed`, `max_frontier_vars`) are cardinality guards — the slow-mode definition, native. The fast two-extremes computation (§6.4) comes later, differentially tested against enumeration, as the strategy already required of fast `I`.
6. **Roles.** (a) First runner of the corpus — the second derivation the 99 hand-derived verdicts have ever had (R5); (b) the `decisions/0006` bakeoff candidate for W2/W3 (#41); (c) controlled test generation (correctness-strategy §5): coverage targets as choice rules plus constraints, `#minimize` for the smallest witness — stronger than generate-and-filter; (d) beyond evaluation: monitoring queries, policy diff, and the MDS readings stage (0002 #5's parked use) are brave/cautious questions over the same program.
7. **Written-down deviations.** Every ASP-visible number is bounded (±2^53, workflows §2; no floats); time is a canonical UTC string or a driver-computed comparison fact; the installed clingo's integer bound is checked at spike time and recorded as a deviation if it bites. **RRULE recurrence is deferred**: scenarios that need generated occurrences (8 cases use it) report `unsupported: recurrence` loudly, not as passes; the first gate is every runnable scenario.
8. **Independence and authority.** `due2-workflows.md` stays normative; the program is a second rendering, and a disagreement is a finding, not an override. The hand corpus (397 scenarios) and the external suites' own answers are the oracle *for* the program; L1–L8 run as properties over its outputs; self-generated vectors test other implementations, never the generator. The program is exactly as trustworthy as the vectors it passes — nothing else endorses it.

## Why

- **Answer sets are the §6.4 completions.** Slow-mode brute force is not merely expressible in ASP; it is what the solver already does. Cautious and brave reasoning are the two quantifiers the verdict definition needs.
- **The audit's failure is not ASP's.** Negation-as-failure collapsed `U` into `F` in the showcase encoding; due2's data model carries the gap as data (fact statuses; the deadline comparison ruled a fact of the SOTW, §5.3; "the assembler computes, never W2", §3.3), so the honest encoding is directly available — and the one-value integrity constraint makes any lapse loud.
- **The writeup argument.** Rule blocks cite their sections (`% workflows §6.1`), so reviewing the program is reading it beside the spec. Python buries the rules in control flow; this is the strongest form of the readable-semantics artefact the spec suite exists to produce.
- **SWI-Prolog, examined and set aside.** It wins implementation comfort — unbounded integers, native dates, one runtime with Turtle parsing, a tracer — but loses both stated goals: completions and controlled generation are native in ASP and hand-rolled in Prolog, and it is a new entrant with no record where clingo already has three slots (#41, the audit, the MDS readings candidate). Its "no driver" advantage is small here: 0007 already requires a driver for digests, canonical bytes, and vector authoring, and §2.4 already quarantines RDF. Revisit triggers below.

## Consequences

- 0002 #1 is superseded for W2/W3 and the oracle. Its stage-1 scope — identity, lineage, canonical bytes, the Dafny `Den` oracle (#8) — is untouched: functional, host-side. Runtime adoption of clingo (or anything) remains its own record, per 0002 #1's revisit trigger.
- The Python W2/W3 backend withdraws from the bakeoff (#39 closes); the bakeoff runs clingo (#41) against Elixir (#40), with the hand corpus as the shared oracle and the brute-force W3 (#38) demoted to a test-tree checker for disagreements.
- Issue #9 becomes the semantics program: driver and flattener, the status matrix and Kleene tables as ASP facts, the one-value integrity constraint, then the runnable corpus scenarios. First spike: `spikes/clingo-i/`, implementing the suite's `interpret` task (`spikes/README.md`).
- #42's bounds bound the ASP enumeration as they bounded slow `I`.

## Revisit when

- The program is asked to become a runtime, not a spec/oracle/generator → the host question (`implementation-alternatives-ii.md`); SWI and the BEAM re-enter there.
- The date and decimal driver compromises hurt — real policies needing in-engine arithmetic → theory propagators, or SWI as host.
- A real policy needs recurrence → driver-side RRULE expansion first (occurrences as facts); in-engine only if that fails.

## References

- Review inputs, 2026-10-16 (repo owner, and a parallel review): min/max Kleene over `f < u < t`; the one-value integrity constraint; the bounded-integer deviation; controlled generation via choice rules; the SWI-Prolog comparison.
