# 0040 — Facts are kept per source, and W2 combines them

**Status:** Decided, 2026-10-26 (the owner, on #137)
**Context documents:** `due2-workflows.md` §3.3, §3.4, §5.4, §7.1 · `due2-profiles.md` §3 · `due2-platform.md` §1.4, §2.4, §3.1 · `decisions/0008` · `decisions/0016` · issues #1, #137

## Question

In `due2-workflows.md` v0.49 the SOTW held one `fact (property | status)` per state property, its values in `fact_value (property, value)`, and an `attribution (property, source | observed_at)` per source. The config's `admit_source (property, source)` and `admit_age (property | max_age)` said that a value from a source not admitted for its property, or observed longer than `max_age` before `effective_at`, is treated as `missing`.

The two did not fit together. A `fact` held one status and one set of values per property, so by the time W2 saw it, the answers of several sources had already been combined into one. W2 could not drop one source's answer and keep another's. `due2-workflows.md` §3.3 said only that "two sources that disagree about the same fact at the same time are a `conflict`", without saying who applies that rule. The orchestrator would have had to, when it froze the SOTW, and there no oracle tests it.

Two questions follow. Where are several sources' answers combined? And who checks that an answer is fresh enough?

## Decision

1. **The SOTW keeps each source's answer.** The relations are `fact (property, source | status: Enum)` and `fact_value (property, source, value: Term)`. Each `fact` is one source's answer, and its status comes from the resolution table of `due2-profiles.md` §3 applied to that source's values. A source that could not be asked, or did not answer, gives `unresolved`. `attribution` is dropped, and an answer's time is the `valid_at` of its event (`due2-workflows.md` §7.1).
2. **The case records answers, not combinations.** The orchestrator asks the SOTW service, and records each answer in the case as an event, as the service returned it. The SOTW of an evaluation takes, for each property and source, the answer with the latest `valid_at` no later than `effective_at`.
3. **W2 combines the admitted answers of each property.**
   - *Admitted.* An answer counts when `admit_source` lists its source for the property. A property with no `admit_source` tuples admits every source, as a duty with no `signer` tuples accepts every issuer (`due2-workflows.md` §3.4).
   - *Answers with values.* These are the admitted answers whose status is `resolved` or `conflict`. If there are any, the combined status is `resolved` when all of them are `resolved` with the same values, compared as sets of written terms (`due2-workflows.md` §2, `Term`), and `conflict` otherwise. A `resolved` answer for a set-valued operand with no members counts too. The combined values are those of these answers. An admitted answer without values is then ignored.
   - *No answer with values.* The combined status is `unresolved` if any admitted answer is `unresolved`, otherwise `invalid` if any is `invalid`, otherwise `missing`. A property whose answers are all from sources that are not admitted is `missing`, as `due2-profiles.md` §3 decided.
   - *No answer at all.* A property with no `fact` is read as `unresolved`, as before (`due2-workflows.md` §5.4).

   Everything that read a fact's status reads the combined status: the truth value of the part, and the `status` of `unknown_part` and `witness_part`.
4. **Freshness is the SOTW service's.** `admit_age` is dropped. When a value changes in the world, the SOTW service supplies the new value, and it reaches the case as a new event. A re-evaluation reads the answers already in the case and asks no source again. Neither the orchestrator nor the evaluator checks an answer's age. A lookup that returned `unresolved` may still be retried (`due2-platform.md` §3.1 step 10), because it was asked but not answered.

## Why this holds

- **The case is a record of what was asked and answered.** Keeping each answer as it came lets the ledger show who said what. Combining is then a pure function of recorded inputs, so replay re-derives which answers counted, and an oracle can test the rule.
- **Admission by source still has work to do.** The orchestrator asks only admitted sources, but answers that nobody asked for still reach the case. A person may volunteer a fact through an intelligent service, and `due2-platform.md` §1.4 records it with that person as its source. It is in the case because it happened, and it must not decide the verdict unless the person is admitted for that property.
- **An answer without values cannot outweigh one with values.** `missing`, `invalid`, and `unresolved` give the part no value to compare. Ignoring them when another admitted source has values loses nothing that the value would not decide. Two sources that give different values cannot both be right, so they are a `conflict`, which is an opaque `U` (`decisions/0016`). With no values, `unresolved` wins, because only an `unresolved` part is completed (`decisions/0016`), and a source that did not answer may still have a value. This follows the existing reading of a single `unresolved` source.
- **A freshness check would make the evaluation a pre-evaluation.** If the evaluator or the orchestrator compared each answer's age with `effective_at`, every evaluation would first evaluate the SOTW against a second policy, the age limits, before evaluating the request. In the owner's words (#137), that "becomes a pre-evaluation of the policy and its SOTW", and it is not a good idea. Keeping values current is the job of whoever owns them, so the source tells the case when a value changes.

## Rejected

- **The orchestrator combines the answers when it freezes the SOTW.** W2 would stay as it was, but the rule would live in impure code that no oracle tests, and the ledger would hold combinations rather than what the sources said.
- **A stale answer is treated as `missing` (the rule of v0.49).** An answer would turn into `U` silently as time passes, and the orchestrator could not tell a value nobody holds from one that is merely old.
- **A stale answer makes `decide` fail with an error.** The orchestrator would then have to re-ask every source before each re-evaluation, so a re-evaluation would no longer read only what the case holds.

## Consequences

- `due2-workflows.md` v0.50:
  - §3.3: `fact` and `fact_value` are keyed by source, `attribution` is dropped, and *Several sources* states item 3.
  - §3.4: `admit_age` is dropped, and the `admit_source` rule follows item 3.
  - §5.4 and §7.1 read the combined status and the answer per property and source.
- `due2-profiles.md` §3: *Admissibility* keeps `admit_source` and gives freshness to the SOTW service.
- `due2-platform.md`: §1.4, §2.4, and §3.1 follow. How the SOTW service tells the orchestrator of a change is left to the platform's revision of the SOTW services (`due2-platform.md` §2.4).
- `schema/collections.schema.json` is regenerated.
- `conformance/README.md`: the case format's facts carry no source, so each is read as one admitted source's answer. The coverage gap names the combination of sources and `admit_source`, which need a `source` field on `sotw.facts` (#1). Three RL2 cases' `notes` are revised, two of which named `admit_age`.
- RL2 filters each fact by a validity interval before resolving it (RL2's `spec/RL2_Model.md` §4.4). due2 does not, so a translated case's stale value is the SOTW service's to replace.

## Revisit when

- A deployment has a source that cannot report changes, and its values go stale between evaluations.
- Two sources must be ranked rather than compared, so that one source's value outweighs another's.

**Note (2026-10-26, `decisions/0045`):** `admit_source` moves out of the evaluation and into the connector registry. The orchestrator records a fact answer only from a source registered for the property, so every answer a case records is admitted, and W2 combines them by item 3.

**Note (2026-10-26, `decisions/0046`):** a changed value reaches a case through an explicit call to the orchestrator: `record_facts`, with answers the caller brings, or `refresh`, which asks the registered sources again. There is no subscription. `refresh` answers the first revisit condition above without checking an answer's age.
