# 0009 — The semantics live in a clingo program: the L9 oracle and the generator

**Status:** Decided, 2026-10-16 (amended the same day: scope narrowed to the oracle and generator roles; see the end); role (d), the bakeoff entrant, lapses with the bakeoff, and the production evaluator is chosen under `decisions/0027`, not by the bakeoff that #1 and the Consequences name
**Supersedes:** `decisions/0002` #7 and its amendment's clarification 1 as to vehicle — the L9 oracle is the clingo program, not a Python direct interpreter. `decisions/0002` #1 (the workflows stay Python) and #5 (clingo stays out of the evaluator pipeline) stand: the program is an oracle and a generator, not a pipeline stage.
**Context documents:** `decisions/0002` · `decisions/0006` · `due2-workflows.md` §5–§6, §6.4 · `correctness-strategy.md` §1.1, §3–§5, §8 · `implementation-alternatives.md` §5 (the 2026-10-10 clingo audit), §7 · `ways-of-working.md` §2.4, §5.1 · issues #9, #36–#42

## Question

The L9 oracle and the generators were to be Python (`decisions/0002` #7, `correctness-strategy.md`): a Python ODRL parser and a direct interpreter beside the evaluator they check. Can the semantics instead be written once, declaratively, as a readable rendering of workflows §5–§6 that runs the corpus, serves as the L9 oracle, and drives controlled test generation, with the semantics and the laws unchanged?

## Decision

1. **The ODRL evaluation semantics are written once, as a generic ASP program (clingo) over flattened ODRL.** It is the L9 oracle `I` (`correctness-strategy.md` §3) and the generator of §5. Workflows §1–§8, the relations, and L1–L9 are unchanged: this changes the oracle's vehicle, not the semantics. No Python direct interpreter is built. The production evaluator is not decided here: W1–W3 remain `decisions/0002` #1 and the `decisions/0006` bakeoff, and adoption needs its own record.
2. **The authored form first.** The shared suite's first task is `interpret` (`spikes/README.md`), whose vectors are the corpus, so the first spike (`spikes/clingo-i/`) reads the authored policy. The Python driver parses the Turtle and makes a purely syntactic flatten of the graph to facts: no lifting, no expansion, no DNF. Those are the program's structural rules, so the program is the direct interpreter over the authored form (`decisions/0002` amendment 1), and L9 is the differential between it and the pipeline once W1 exists. Relation-level vectors (#36) come later, for the bakeoff (#41), as a second input face of the same rules. Digests, canonical bytes, and id minting stay host-side (`decisions/0007`, `ways-of-working.md` §2.4): they are the functional parts the 2026-10-10 audit named as alien to a logic engine.
3. **Encoding obligations: the gate the audit failed.**
   - `U` is data, never negation-as-failure. Fact statuses (`resolved/missing/invalid/conflict/unresolved`), deadline comparisons (§5.3: a fact of the SOTW), and witness timeliness arrive as facts.
   - Every part carries exactly one of `t/f/u`, enforced by an integrity constraint from day one, so a forgotten rule fails loudly instead of yielding a silent false.
   - Kleene conjunction and disjunction are min/max over `f < u < t`; `dprod:not` is the involution.
   - **The evaluation layer is stratified Datalog.** Choice rules, and anything else that makes an answer set non-unique, appear only in the completion (5) and the generator (6c). Given one completion, the evaluation is a single, deterministic, stratified model. This keeps the evaluation rules readable as plain derivations, and portable to a Datalog engine if the program ever needs one.
4. **Numbers and time.** clingo's integers are 32-bit signed. workflows §2's ±2^53 bound covers JSON counts and bounds only, so it does not make values fit. The program compares; it never computes.
   - Integers within 32 bits pass through.
   - Every other compared value reaches the program as an order-preserving integer rank within its value space: instants, decimals, and wider integers. The driver also supplies the instant-plus-duration sums that relative deadlines need (§5.3).
   - No value is truncated, rounded, or dropped. A value the driver cannot place is reported as unsupported, loudly.
   - There are no floats.
5. **Completion is answer-set enumeration.** One choice rule per unknown literal (the canonical-literal key of workflows §6.4) yields one answer set per completion. A verdict is definite iff it is cautious-entailed. This is slow mode, the §6.4 definition, with no uniform/mixed split; above a variable cap on the unknown literals (for example 16) it declines rather than falling back (`correctness-strategy.md` §3). `max_mixed` and `max_frontier_vars` are the fast computation's limits (W3, `decisions/0004`), not slow mode's. Fast mode (the two extremes) comes later, differentially tested against enumeration below the cap.
6. **Roles.**
   - **(a) Corpus runner.** The program is the first runner of the corpus: the second derivation the hand-derived verdicts have ever had (R5).
   - **(b) L9 oracle.** It is the L9 oracle against the pipeline, once W1 exists.
   - **(c) Generator.** It drives controlled test generation (`correctness-strategy.md` §5). Coverage targets are choice rules plus constraints, and `#minimize` gives the smallest witness, which is stronger than generate-and-filter.
   - **(d) Bakeoff entrant.** It is the Clingo entrant in the `decisions/0006` bakeoff (#41) on relation-level vectors, under that record's gate.
   - **(e) Later.** Monitoring queries, policy diff, and the MDS readings stage become brave or cautious questions over the same program.
7. **RRULE recurrence is deferred.** Scenarios that need generated occurrences (8 cases use recurrence) report `unsupported: recurrence` loudly, never as passes. The first gate is every runnable scenario. Deadlines and durations are in scope via (4).
8. **Independence and authority.** `due2-workflows.md` stays normative. The program is a second rendering, and a disagreement is a finding, not an override.
   - The hand corpus (`conformance/cases/`) and the external suites' own answers are the oracle *for* the program.
   - L1–L8 run as properties over its outputs.
   - Self-generated vectors test other implementations, never the generator.
   - The program is exactly as trustworthy as the vectors it passes.
   - If the Clingo bakeoff backend (#41) reuses the program's rules, L9 between them shares those rules. `correctness-strategy.md` §3 records that common mode. The independent checks there are the hand corpus, the brute-force W3 (#38), and the other backends.

## Why

- **Answer sets are the §6.4 completions.** Slow-mode brute force is not merely expressible in ASP; it is what the solver already does. Cautious and brave reasoning are the two quantifiers the verdict definition needs.
- **The audit's failure is not ASP's.** In the showcase encoding, negation-as-failure collapsed `U` into `F`. due2's data model instead carries the gap as data: fact statuses; the deadline comparison ruled a fact of the SOTW (§5.3); "the assembler computes, never W2" (§3.3). So the honest encoding is directly available, and the one-value integrity constraint makes any lapse loud.
- **The writeup argument.** Each rule block cites its section (`% workflows §6.1`), so reviewing the program means reading it beside the spec. A Python interpreter buries the rules in control flow. The rule blocks are the strongest form of the readable-semantics artefact that the spec suite exists to produce, and the input to generation elsewhere.
- **SWI-Prolog, examined and set aside.**
  - It wins on implementation comfort: unbounded integers, native dates, one runtime with Turtle parsing, and a tracer.
  - It loses both stated goals. Completions and controlled generation are native in ASP and hand-rolled in Prolog.
  - It would be a new entrant with no record. Clingo already has one: the 2026-10-10 audit, `decisions/0002` #5's MDS readings stage, and the bakeoff (#41).
  - Its "no driver" advantage is small here: `decisions/0007` already requires a driver for digests, canonical bytes, and vector authoring, and `ways-of-working.md` §2.4 already quarantines RDF.
- **Datalog engines, examined and set aside.**
  - ExDatalog (pure Elixir, semi-naive with stratified negation and aggregates, v0.5.0) computes one model. Completions would have to be enumerated by hand, and it cannot generate. It is also immature (one dependent), and it would tie the oracle to the BEAM, which is a bakeoff candidate (#40) the oracle must stay independent of.
  - Soufflé was set aside in `implementation-alternatives.md` §7.
  - What Datalog offers — a deterministic, stratified, reviewable evaluation — is kept as the discipline in decision 3. The same evaluation rules then run in clingo with ASP's completion and generation on top.

## Consequences

- `decisions/0002` #7's Python direct interpreter is not built. 0002 #1 and #5 stand, and 0002 #2's Dafny `Den` oracle (#8) is untouched.
- The `decisions/0006` bakeoff is unchanged in gate and scoring. Clingo (#41) and Elixir (#40) run first, against the brute-force W3 (#38) as 0006 #4 requires. The Python backend (#39) is deferred, not withdrawn: it may enter when the production evaluator is written.
- `correctness-strategy.md` register #3 (`I` and W1 share the parser) narrows: only the Turtle reading is shared. The lifting is the program's. The driver is tested on its own (strategy §4.1).
- Issue #9 becomes the semantics program. Its first spike is `spikes/clingo-i/`, implementing the suite's `interpret` task (`spikes/README.md`).
- The variable cap of `correctness-strategy.md` §3 bounds the ASP enumeration as it bounded slow `I`. It is not #42, which bounds the input-space enumerator (§1.1).

## Revisit when

- The program is asked to become a runtime, not an oracle or generator → that is an adoption record (`decisions/0002` #1, #5; `implementation-alternatives-ii.md`). SWI and the BEAM re-enter there.
- The rank and sum encoding hurts: a real policy needs in-engine arithmetic → theory propagators, or SWI as host.
- A real policy needs recurrence → driver-side RRULE expansion first (occurrences as facts); in-engine only if that fails.

## References

- Review inputs, 2026-10-16 (repo owner, and a parallel review): min/max Kleene over `f < u < t`; the one-value integrity constraint; the bounded-integer deviation; controlled generation via choice rules; the SWI-Prolog and ExDatalog comparisons.

## Amendment (2026-10-16, same day)

The first version of this record went further than the owner agreed, and stated four things wrong. The decision above is the corrected text:

- **Scope.** The first version said "Python builds no evaluator", withdrew the Python bakeoff backend (#39), demoted the brute-force W3 (#38), and superseded 0002 #1 for W2/W3. The owner adopted clingo for the oracle and generator roles only. The production evaluator stays with 0002 #1 and the 0006 bakeoff, and Python may still be spiked when it is written.
- **The caps.** The first version called `max_mixed` and `max_frontier_vars` slow mode's caps. Slow mode's cap is the variable cap of `correctness-strategy.md` §3.
- **Numbers.** The first version bounded ASP-visible numbers at ±2^53 "by workflows §2". That bound covers JSON counts only, and clingo's integers are 32-bit.
- **Order and driver.** The first version said both "relation-level vectors first" and "the whole grammar first", and described the driver as flattening into relation facts in one place and syntactically in another. The authored form comes first, and the flatten is syntactic.
- **Additions.** The amendment also adds the stratified evaluation layer (decision 3), the Datalog comparison, and the common-mode note in 8.
