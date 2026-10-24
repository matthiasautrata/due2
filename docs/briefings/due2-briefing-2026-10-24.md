# due2: ODRL policy evaluation that says when it does not know

**Status, as of commit `c711e89`.** due2 has a specification, a conformance corpus, checkers, a reference oracle, and formal models of its central claims. It has no evaluator. The oracle, `spikes/clingo-i`, answers 400 of the corpus's 438 scenarios as the hand-derived answers expect, and declines the other 38. Its tests now include a bounded-exhaustive search: every input up to a stated size, 73,876 of them at the largest bounds. Alloy models of the five formal claims (`correctness-strategy.md` §4.8) find no counterexample within their stated bounds, after finding a flaw in the spec's completion key, since fixed, and one in a draft decision, fixed before it was decided. No Lean proof exists yet. The repository holds 26 decision records and 137 corpus cases, and CI runs every check on every push.

This briefing is for engineers who will meet due2 without having followed its design. It says what due2 does, and what its tests do and do not establish. The second half teaches the reasoning behind the tests, because a test number means nothing until you know what was sampled, what it was compared against, and what could still get through. It supersedes `due2-briefing-2026-10-21.md`, which described commit `ce17910`; Section 0 says what changed since. Every code excerpt and every output below is copied from the repository or from a run at `c711e89`. Every number comes from a run or a cited record; nothing is reconstructed.

## Contents

0. What changed since the first briefing
1. What due2 is
2. Why unknown must not become false
3. How a verdict is decided
4. The pieces
5. How we know it is right: a primer on reading test numbers
6. What runs, with numbers
7. Assessment
8. Recommendations
9. Appendix A: each check, with a real example
10. Appendix B: how unknowns are handled
11. Appendix C: three answers and one planted bug, walked
12. Appendix D: sources for the statistics

## 0. What changed since the first briefing

The first briefing ended with a sequence of next steps (its Section 8). The first two are done, and the formal models answered an open question. The bullets use terms that later sections define: a *frontier* and its *routes* in Section 3.1, the claims K, M, F, W, and P in Section 7.2 item 5, and an Alloy *scope*, the bound on an Alloy search, in Section 5.7.

- **The bounded-exhaustive search over clingo-i is built** (#42, #44). Nine *spaces*, each an answer set program whose answer sets are every input up to a bound, check clingo-i against its brute-force oracle on every input. Each of the 23 planted bugs is now exposed by a space with no help from hand-written examples, including the two that random generation never reached. Sections 5.5 and 5.6 have the numbers.
- **The spaces check two claims** (#85). Monotonicity (M) and the basis waiver (W) hold on every input at the largest bounds. W, which had one hand-written example as its only evidence, now has 67 inputs of its shape, which a search of 6,000 random cases never reached (#77).
- **Each claim has an Alloy model** (#84, `formal/alloy/`). The models of K, M, F, W, and P search for counterexamples among every small instance. They found two real flaws (Section 7.1): a gap in the spec's completion key, fixed by `decisions/0023`, and an unsound fallback for the listed frontier in a draft of `decisions/0026`, fixed before it was decided.
- **Question P is settled** (`decisions/0026`). Under unknowns, the frontier a `Pending` reply lists is now the non-dominated routes that *suffice*, and P has become a claim. Section 3.1 explains it.
- **Four more decisions:** a repeated member of a logical constraint is malformed (`decisions/0022`), with two new negative cases; the completion key includes the concept reading (`decisions/0023`); a `dateTime` has a timezone and a `date` none (`decisions/0024`); and a set-valued operand takes only the set operators (`decisions/0025`).
- **A platform map.** `due2-platform.md` sketches the components around the evaluator: fact fetching, the case history, and storing traces. Every section of it is open.

## 1. What due2 is

ODRL 2.2 is the W3C's language for writing data-usage policies: permissions, prohibitions, and obligations about who may do what with which asset, under which constraints. It standardises how a policy is written. It does not say how to evaluate one. It gives no rule for missing data, no ordering across XML Schema datatypes, no lifecycle for duties, and an incomplete account of conflicts.

due2 is a specification of how to evaluate ODRL 2.2 policies, plus everything needed to check an implementation of it. An evaluation takes three inputs: a policy, an access request, and a frozen *state of the world* (SOTW), which holds the facts and the evidence of performed duties. It returns one of five verdicts:

| Verdict | Meaning |
|---|---|
| `Permit` | Some permission applies, nothing overrides it, and its duties are met |
| `Deny` | A prohibition applies and survives conflict resolution |
| `Pending` | A permission applies but waits on duties not yet performed. The answer lists them as the *frontier* |
| `NotApplicable` | Nothing applies |
| `Indeterminate` | The answer depends on information the evaluator does not have. The answer names that information and the range of verdicts it could produce |

The design is in four specifications, about 24,450 words in total (`docs/spec/`), and 26 decision records (`docs/decisions/`). Start with `README.md` and `due2-architecture.md` §0.

## 2. Why unknown must not become false

Most evaluators read a fact they do not have as false. That is wrong in both directions. If the missing fact sits in a prohibition's constraint, the prohibition does not apply, and the request is let through. That is a silent bypass. If it sits in a permission's constraint, a legitimate request is refused with no explanation of what would fix it.

due2 uses three truth values: true (`T`), false (`F`), and unknown (`U`), combined by strong Kleene logic. `T and U` is `U`, `F and U` is `F`, `T or U` is `T`. A value that is missing, malformed, in conflict, or not yet looked up makes its part of a rule `U`, and the `U` carries through to the verdict (`ways-of-working.md` §5.1). The repository's own notes say every external evaluator examined gets this wrong (`conformance/external/README.md`).

A real case shows the kind of question this decides. `conformance/cases/dprod-audit-logs` has an obligation to delete audit logs whose retention exceeds seven years:

```turtle
rule:audit-retention a odrl:Duty ;
    rdfs:label "7-year retention limit" ;
    odrl:action odrl:delete ;
    odrl:constraint [
        a odrl:Constraint ;
        odrl:leftOperand ex:retentionPeriod ;
        odrl:operator odrl:gt ;
        odrl:rightOperand "P7Y"^^xsd:duration
    ] .
```

One scenario states the retention as `P730D`, 730 days. The corpus's expected answer reports the obligation `unknown`, and its `why` reads:

> The retention guard is U: P730D is a day-time duration, P7Y a year-month one, and gt is undefined across kinds (due2-profiles.md §4) — the operand is invalid, not false, so the constraint is U and the obligation in force is reported unknown. Whether a 730-day retention exceeds seven years is a real question with a real answer (it does, barely), but it is not decidable from these two terms, and due2 says so rather than guessing.

An evaluator that read the failed comparison as false would have dropped the obligation without saying so.

## 3. How a verdict is decided

The rule is called *invariance over completions* (`due2-workflows.md` §6.4). Each unknown that could take a value in the real world is a variable. A *completion* assigns `T` or `F` to every variable. If every completion gives the same verdict, that verdict is the answer. If completions disagree, the answer is `Indeterminate`, with the lowest and highest verdicts they reach.

Checking every completion costs 2ⁿ evaluations for n variables. The spec proves (`due2-workflows.md` §6.4) that the verdict is monotone, so two completions suffice: the most restrictive one and the most permissive one. Every other completion's verdict lies between them. That proof is claim M of `correctness-strategy.md` §4.8, and it is one of the things the tests below are built to attack.

Three details make the rule exact:

- **Canonical literals** (`decisions/0012`). Two constraints that test the same operand against the same value are one variable. The rule that decides when two parts share a variable is the *completion key* (claim K of `correctness-strategy.md` §4.8). An operator and its complement (`lt` and `gteq`, `eq` and `neq`) share one variable with opposite polarities. Without this, `x < 18` and `x >= 18` could both be true in some completion, and the answer would be `Indeterminate` where it should be definite.
- **Only unresolved values are completed** (`decisions/0016`). A state fact that has not been looked up, or whose lookup failed, has a real value nobody knows yet, so it is completed. A value that is missing, malformed, or in conflict has no single value that fits. It is *opaque*: a variable of its own, never paired with another part.
- **The answer explains itself** (`decisions/0010`, `decisions/0011`). The reply names the rules that decided it (`verdict_basis`), the rules removed and by what (`eliminated`), the duties outstanding (`frontier`, `obligations`), and every unknown input (`unknown_parts`). For `Indeterminate` it gives `verdict_range`.

A real reply, from `clingo-i` on `conformance/cases/rl2-anonymization-required`, scenario "assessment missing". The permission requires an approved anonymization assessment, and the SOTW has none:

```json
{
  "verdict": "Indeterminate",
  "frontier": [],
  "obligations": [],
  "exact": true,
  "verdict_basis": [{"ref": "https://example.org/processAnonymizedData", "role": "unknown"}],
  "eliminated": [],
  "unknown_parts": [
    {
      "ref": "https://example.org/processAnonymizedData",
      "input": "https://example.org/targetAnonymizationApproved",
      "status": "missing"
    }
  ],
  "verdict_range": {"low": "NotApplicable", "high": "Permit"}
}
```

Appendix C walks this answer and two others.

### 3.1 What a `Pending` asks the requester to do

A permission may carry *preconditions*: duties the requester must perform before it permits. The duties a candidate permission still waits on are its *route*. A `Pending` reply lists routes as its *frontier*: perform every duty of any one listed route, and the request is permitted.

With no unknowns this is plain: list the routes that no smaller route contains. Under unknowns, which routes exist can depend on the unknowns. A duty's precondition may be owed only if some fact holds, or evidence of a duty may be unreadable. `due2-workflows.md` §6.3 (`decisions/0026`) lists a route when it *suffices*: it is a route in some completion, and every completion has a route that is the same set or a subset of it. Performing a route that suffices therefore permits in every completion. The argument is in `decisions/0026`: a performed duty is not violated, conflict resolution never reads duties, and monotonicity (claim M, Section 7.2 item 5) does the rest.

The earlier rule listed only the routes of candidates that were ready or pending whatever the unknowns were. `decisions/0019` found a definite `Pending` whose listed frontier omits a route that every completion offers, because no single permission gives it in every completion. An Alloy model then found worse: replies that are `Pending` and list nothing to do, though every completion agrees on what to do. Under the new rule, `check_completion.py` finds an empty listed frontier in 1 of 942 random definite `Pending` cases, against 191 under the old one. In that one case what to do really does depend on an unknown: one duty is owed when a fact is false, another when it is true. The reply then names the unknown, and says its frontier is incomplete.

## 4. The pieces

The design (`due2-architecture.md`) splits evaluation into three workflows, none of which is implemented:

- **W1, normalisation.** Reads the authored RDF and rewrites compound rules into atomic ones (`odrl-compound-to-atomic-normalization.md`). It rejects what due2 does not admit, with a code from `due2-diagnostics.md`.
- **W2, findings.** Gives each atomic rule a Kleene truth value against the request and the SOTW.
- **W3, resolution.** Resolves conflicts, derives the frontier, and decides the verdict over completions.

What exists:

- **The corpus** (`conformance/cases/`): 137 cases, each a policy plus scenarios with hand-derived expected answers. Format in `conformance/README.md`.
- **The checkers** (`tools/`): `check_corpus.py` checks case format and the admitted profile, and re-implements W1's rejections for the negative cases. `check_odrl22.py` validates policies against ODRL 2.2 with SHACL. `check_completion.py` tests the two-completions shortcut against brute force on an abstract model.
- **The reference oracle** (`spikes/clingo-i`): the spec's semantics as an answer set program, 3,728 lines in 13 files, driven from Python. An answer set solver (clingo) enumerates the completions as answer sets. A verdict that holds in every answer set is definite. clingo-i is how the hand-derived answers get a second, mechanical derivation (`decisions/0009`). It still lists the frontier of the earlier rule of Section 3.1 (#103).
- **The formal models** (`formal/alloy/`): one Alloy model per claim, restated from the spec's text rather than from clingo-i. They run outside README § Verify, in a slow tier that CI does not run yet (Appendix A.17).
- **The case ledger** (`decisions/0008`): an append-only history per case, so a decision can be re-derived later. It is designed (`correctness-strategy.md` §4.7) and not built.

## 5. How we know it is right: a primer on reading test numbers

This section is the reason the briefing exists. Every number in Section 6 is one of the kinds below, and each kind answers a different question.

### 5.1 A test is a sample, checked against an oracle

A test runs some inputs and compares the outputs with expected outputs. Passing shows those inputs work. It shows nothing about the inputs not run. Two questions follow for any suite:

- **Which inputs were sampled, and how?** Hand-picked inputs reflect what the author thought of. Randomly generated inputs reflect what the generator can produce. Neither covers what nobody imagined.
- **Where did the expected output come from?** Whatever supplies it is called the *oracle*. If the oracle and the code share a mistake, the test passes and both are wrong. This is a *common-mode* failure, and it is the main risk in a project like due2, where one reading of one specification feeds every oracle.

due2 has five oracles. None is fully independent of the others:

| Oracle | Where | What it shares with clingo-i |
|---|---|---|
| Hand-derived expected answers | each `case.json` | The same author's reading of the same spec |
| The Python brute-force oracle | `spikes/clingo-i/tests/test_brute_force.py` | The completion key. Its docstring says it "shares only the spec's completion key with it". It also shares the random generator and the author |
| The abstract model | `tools/check_completion.py` | The algorithm of `due2-workflows.md` §6.4, restated much more simply: one policy, flat conjunctions, no recurrence |
| The Alloy models | `formal/alloy/` | The spec's prose and its reading. They restate the spec in a third language, and leave out what each model's header lists |
| External suites' own answers | `rl2_expected`, `force_expected`, … in each `case.json` | Nothing, but they are not trusted either: their semantics are inputs to review (#63), and several were found wrong (Appendix A.2) |

The external answers are the only oracle that shares nothing with due2. That is why the corpus keeps them, and why any difference is explained in the case's `notes`.

### 5.2 Zero failures in n random cases: the rule of three

`check_completion.py` reports "50000 cases, 0 mismatches". What does that support?

Suppose each generated case independently fails with some unknown probability p. The chance that n cases all pass is (1 − p)ⁿ. Ask how large p can be before passing all n becomes a 1-in-20 fluke: solve (1 − p)ⁿ = 0.05, which gives p ≈ 3/n. This is the *rule of three*: after n trials with no failure, you can say with 95% confidence that the failure rate is below 3/n.

For n = 50,000, 3/n is 0.006%. So the honest reading of that line is:

> With 95% confidence, fewer than 6 in 100,000 cases *drawn by this generator* would show a mismatch *between the shortcut and brute force on the abstract model*.

Three limits are built into that sentence:

- **The generator's distribution.** A rule of three says nothing about inputs the generator rarely or never produces. If a flaw shows only on a shape that appears once in a million draws, or never, 50,000 passes are fully consistent with it. Claim W was exactly this case: a 6,000-case search never produced its shape (#77). The bounded-exhaustive spaces of Section 5.6 reach it in 67 inputs.
- **The model, not the system.** The abstract model is not clingo-i, and clingo-i is not the evaluator. `correctness-strategy.md` §4.8 says so in the evidence column for M.
- **Fixed seeds.** `check_completion.py` uses fixed seeds (20261011–20261015), so every run draws the same cases. A re-run with unchanged code repeats the same experiment and adds no information. It adds information when the code or the spec's algorithm changes.

### 5.3 Planted bugs: what they can estimate, and under which assumptions

The idea is old (Mills, 1972), and ecologists use it to count fish. To estimate the fish in a lake, catch 100, tag them, release them, and catch again. If 10 of your second catch of 100 are tagged, you are catching about 10% of the fish, so the lake holds about 1,000. This is *capture–recapture*.

Mills applied it to software. Plant S bugs on purpose, then test. Say testing finds s of the planted bugs and n real ones. If planted bugs are exactly as hard to find as real ones, the tests found the fraction s/S of each kind, so the real total is about N ≈ n × S / s.

A worked example. Plant 20 bugs. Testing finds 15 of them and 30 real ones. The tests catch 15/20 = 75% of bugs, so the real total is about 30 / 0.75 = 40. About 10 real bugs are still in the code.

Mills also gave a confidence for the case everyone hopes for: all S planted bugs found and no real one. Myers' textbook states it. If the claim is "the code had at most K real bugs", and testing found all S planted bugs and at most K real ones, the confidence is C = S / (S + K + 1). For the claim "no real bug remains", K = 0 and C = S / (S + 1).

The intuition for S / (S + 1): suppose one real bug did remain. If it is exactly as findable as each planted bug, then of the S + 1 bugs, each is equally likely to be found last. The chance that the real one comes last, after all S planted ones, is 1 / (S + 1). So "found every planted bug and no real one" would be a 1-in-(S + 1) coincidence if a real bug existed. To reach 99% confidence that no bug remains, you need 99 planted bugs, all found, and no real bug found.

| Planted bugs, all found, no real bug found | Confidence that no real bug remains |
|---|---|
| 10 | 91% |
| 23 | 96% |
| 99 | 99% |

Every one of these numbers rests on three assumptions:

1. **Representative.** Planted bugs are as hard to find as real ones. In practice they are usually easier, so the estimate is optimistic.
2. **Independent.** The tests were not written knowing which bugs were planted.
3. **Fair chance.** Whether a test finds a bug is like a draw, the same for planted and real bugs.

Break any one and the arithmetic still runs, but the answer means nothing.

### 5.4 Why due2's 23 planted bugs are not a Mills estimate

`test_brute_force.py` plants 23 bugs, called *mutants*: 17 in the rule logic and 6 in the duty logic. Each is a one-line edit to clingo-i's program, and the suite must catch every one. It does: all 23 kill tests pass. That does **not** license the sentence "we are 96% confident no bug remains", for three reasons:

1. **They were chosen, not sampled.** Each mutant targets a named risk: an opaque leaf read as false, two parts sharing a variable they should not, a negation ignored. Real bugs also come from elsewhere, above all from misreading the spec, which every oracle in Section 5.1 would share. No mutant represents that.
2. **The tests were tuned to them.** The spike journal records it. On 2026-10-17: deleting the flip constraint and keying literals per part "survived most random runs", so "three @example cases now kill both". On 2026-10-18: "the 6 duty mutants are killed by the explicit cases alone". This breaks the independence assumption, like tagging fish and then fishing where you released them. That was the right engineering move, because those mutants exposed weak spots in the generator. It does mean the kill rate cannot be read as a detection rate.
3. **Twenty-three is few.** Even with every assumption met, 23 kills give 96% confidence, and only about bugs of the planted kinds.

So due2 makes no estimate of how many bugs remain. Nothing in the repository supports one.

### 5.5 What the planted bugs do tell you

They answer two narrower questions well.

**Are the assertions strong enough?** A test that runs code but checks too little passes broken code. This is *mutation testing* (DeMillo, Lipton, and Sayward, 1978): if a deliberate break goes unnoticed, the suite cannot see that kind of break. All 23 kills mean the differential's comparison is sharp enough to see each of the 23 planted errors, and so, plausibly, errors like them. The method assumes that simple faults *couple* to complex ones: tests that catch the simple faults catch most of the complex ones too. Empirical studies support the assumption partly, not fully (Just and others, 2014).

**How strong is the random generator on its own?** The kill tests let explicit examples go first. To see what random generation achieves alone, `spikes/clingo-i/tests/measure_mutants.py` runs each mutant against generated cases only, up to 2,000 of them, with no explicit examples, and records the draw that first exposes it. It repeats this under several random seeds, because one seed gives one sample. These are its results for seeds 0 to 4 (`uv run python -m tests.measure_mutants 5`, from `spikes/clingo-i`, which takes about 31 minutes on one core of a 10-core Mac); rule mutants come first, then duty mutants, each sorted by the last column:

| Mutant | What it breaks | Seed 0 | Seed 1 | Seed 2 | Seed 3 | Seed 4 | Draws per exposure |
|---|---|---|---|---|---|---|---|
| `unknown-parts-of-f-atoms` | Reports the `U` parts of an `F` rule, which no unknown can change | 7 | 3 | 3 | 5 | 7 | 5 |
| `u-atoms-remove` | Treats a `U` rule as surely applying | 8 | 5 | 4 | 7 | 3 | 5 |
| `opaque-atoms-share-a-variable` | Gives every opaque finding one shared variable | 8 | 5 | 4 | 10 | 3 | 6 |
| `not-as-identity` | Lets negation pass its operand's value through unchanged | 11 | 9 | 41 | 7 | 5 | 15 |
| `and-or-swapped` | Swaps Kleene `and` and `or` | 9 | 14 | 41 | 7 | 5 | 15 |
| `flip-constraint-deleted` | Marks every unknown pivotal, even one that moves nothing | 12 | 18 | 120 | 31 | 3 | 37 |
| `opaque-leaf-as-f` | Reads an opaque leaf as `F`: unknown as false | 47 | 81 | 44 | 35 | 3 | 42 |
| `variable-per-leaf` | Gives each leaf its own variable, so equal constraints vary independently | 12 | 9 | 107 | 46 | 67 | 48 |
| `xone-unknown-as-false` | Reads a `U` member of an `xone` as `F`, the shortcut a counting evaluator is likely to take | 47 | 9 | 85 | 26 | 80 | 49 |
| `xone-many-true-as-t` | Reads an `xone` with two or more `T` members as `T`, as `or` does | 11 | 9 | 106 | 197 | 5 | 66 |
| `live-ignores-negation` | Lets a negation pass liveness on without flipping it | 170 | 18 | 154 | 122 | 67 | 106 |
| `u-leaf-of-f-atom-named` | Names a `U` leaf that only `F` rules read | 90 | 18 | 154 | 363 | 67 | 138 |
| `polarity-ignored` | Reads a complement as its base: `neq` as `eq` | 87 | 106 | 414 | 160 | 113 | 176 |
| `missing-paired` | Pairs a missing leaf as if it were unresolved, which `decisions/0016` forbids | 708 | 87 | 422 | 159 | 138 | 303 |
| `unknown-parts-of-u-atoms-only` | Drops the `U` parts of a `T` rule | 155 | 1,448 | 216 | 122 | 151 | 418 |
| `live-xone-ignores-term` | Lets an `xone` term pass liveness on whatever its siblings are | 193 | 191 | 1,540 | 1,376 | 187 | 697 |
| `live-negated-xone-ignores-terms` | Lets a negated `xone` pass liveness on whatever its siblings are | — | — | — | — | — | — |
| `duties-never-unknown` | Never names a duty finding as unknown | 11 | 78 | 43 | 14 | 21 | 33 |
| `fulfilled-u-as-f` | Reads a `U` fulfilment as `F`: unknown as false | 11 | 181 | 43 | 14 | 82 | 66 |
| `fulfilled-share-a-variable` | Gives every `U` fulfilment one shared variable | 442 | 341 | 45 | 16 | 328 | 234 |
| `duty-roots-negated` | Reads an obligation's guard negated | 1,105 | 1,936 | 1,097 | 541 | 680 | 1,072 |
| `in-force-guards-ignored` | Decides a `U` obligation from its policy match alone, dropping its guards | 1,344 | 78 | — | — | 341 | 1,921 |
| `violated-u-owed-listed` | Lists a candidate whose precondition is violated as if it waited on the others | — | — | — | — | — | — |

A dash means that none of the 2,000 draws exposed the mutant. The last column is the best single estimate of how many draws it takes, on average, to expose the mutant: the draws used across all five seeds, a dash counting as 2,000, divided by the number of seeds that exposed it. It is the inverse of the per-draw exposure rate, estimated by maximum likelihood with the dashes treated as censored: each says only that exposure takes more than 2,000 draws.

How to read the table:

- **Two mutants survive all 10,000 draws.** No seed exposes `live-negated-xone-ignores-terms` or `violated-u-owed-listed`. By the rule of three, with 95% confidence the generator exposes each in fewer than 3/10,000 = 0.03% of its draws. A real bug that shows only on the same shapes would likely slip past random generation too, and only an explicit example would catch it. This is the most useful output of the exercise: it points at the generator's blind spots. The bounded-exhaustive spaces (`correctness-strategy.md` §1.1 and §5, #44) reach both (see below).
- **Two more are rare, not unreached.** `in-force-guards-ignored` survives seeds 2 and 3, and `duty-roots-negated` is exposed under every seed, but only after about 1,072 draws on average. Both have an explicit example, so the kill tests catch them either way.
- **The bounded-exhaustive spaces expose all 23.** `test_spaces_alone_expose_mutant` (slow tier) asserts that each mutant is exposed by the inputs of one space at one bound, with no explicit example and no randomness; `spikes/clingo-i/TESTS.md` names each mutant's space. The two mutants generation never reaches need the slow bounds of the `xone` and `guards` spaces. `flip-constraint-deleted` needs the slow `conflicts` space, though generation exposes it within about 37 draws. So each method reaches mutants the other reaches late or not at all, and no test asserts the numbers in this table.
- **One seed's number is noisy.** If each draw exposes a mutant with probability p, the draw of first exposure follows a geometric distribution with mean 1/p and a standard deviation almost as large. `live-xone-ignores-term` is first exposed at draw 187 under one seed and 1,540 under another; `unknown-parts-of-u-atoms-only` at 122 and 1,448; `duty-roots-negated` at 541 and 1,936. One run gives an order of magnitude at best. The last column, pooled over five seeds, is steadier, but even it rests on five samples.
- **Eleven mutants need more draws on average than the kill tests' budget of 100** (`max_examples=100` in `spikes/clingo-i/tests/test_brute_force.py`), counting the two never exposed. Among the rest, `in-force-guards-ignored` needs about 1,921, `duty-roots-negated` about 1,072, and `live-xone-ignores-term` about 697. Without their explicit examples, the kill tests would likely miss them.
- **Columns are not independent samples.** Within one seed every mutant sees the same sequence of draws, so one draw that exposes several mutants gives them the same number: `opaque-atoms-share-a-variable` and `u-atoms-remove` share 8, 5, 4, and 3 under seeds 0, 1, 2, and 4, and `not-as-identity` and `and-or-swapped` share 41, 7, and 5 under seeds 2 to 4. Different seeds are independent; different mutants under one seed are not.
- **A trend from single runs is not a trend.** The spike journal records `polarity-ignored` first exposed at draw 1,030, then 759, then 175, as the generator was improved. Five seeds of today's generator give 87 to 414 for the same mutant, so part of that apparent trend is within one generator's noise. Compare generators by the pooled column, over the same seeds.

### 5.6 Covering the input space on purpose

Random generation explores where the generator tends to go. Two techniques push it elsewhere.

**Shape tallies.** A test counts how often the generator produces each hard shape, and fails if one never appears. For example, "Indeterminate with a non-pivotal u atom": an unknown that cannot change the answer, which the reply must not name. clingo-i tallies 12 rule-level shapes over 400 fixed-seed draws and 9 duty shapes over 1,000. Today each shape must appear at least once. `correctness-strategy.md` §4.8 asks for more: each claim's hard shape reached in a stated share of draws (#77).

**Bounded-exhaustive search.** Enumerate every input up to a small size and check each one. The *small-scope hypothesis* (Jackson, *Software Abstractions*) is the observation that most design bugs already show on small inputs. Zero failures then mean no failure within the bound, which is a guarantee for that bound, not a sample.

clingo-i's enumerator is a set of nine *spaces* (`spikes/clingo-i/TESTS.md` § The bounded-exhaustive spaces). Each is a small answer set program in `spikes/clingo-i/tests/space/` whose answer sets are the inputs: choice rules pick the rules, their constraint trees, how each operand is given, and the conflict strategy, and in the duty spaces the duties and their guards, deadlines, and evidence. A space chooses only what is checked. The expected answer still comes from the brute-force oracle. Each space has two bounds, measured rather than guessed: a *PR bound*, 6,126 inputs in all, that runs in README § Verify, and a *slow bound*, 73,876 inputs, that runs with `uv run pytest -m slow` in about 14 minutes on ten cores.

Three guards keep the spaces honest:

- **Counts.** Symmetry constraints drop inputs that differ only by an order or a renaming the semantics ignores. One that dropped too much would shrink a space silently, since every remaining input still passes. So `test_space_has_its_count` checks each space's size against a count computed in Python, without clingo.
- **Shapes.** The slow spaces must reach every shape that the shape tallies require of the random generators.
- **Mutants.** Each of the 23 mutants must fail on some input of a named space and bound, with no hand-written example and no random draw (`test_spaces_alone_expose_mutant`). The two mutants that no random seed exposes (Section 5.5) are exposed this way. `live-negated-xone-ignores-terms` first fails on input 8,180 of the `xone` space at its slow bound, a negated `xone` inside an `or` that `TESTS.md` walks.

### 5.7 Proof, and what proof cannot cover

A proof covers every input, which no test can. But it covers a model, and the model is a reading of the spec. `decisions/0021` follows Cedar's pattern: a small executable model in a prover, proofs about the model, and differential tests between the model and every implementation, so the object proved is the object tested. It is also explicit about the limit (#6): whether due2 reads ODRL 2.2 and DPROD as their authors intended cannot be a theorem. Only outside answers can test that.

The order matters. `decisions/0021` #3: counterexample search comes before proof, because a search is cheap and a proof of a false claim is expensive to fail at. due2 has done the search. Alloy (Jackson) checks a claim against every instance up to a *scope*, a bound on how many of each kind of thing an instance has. A `check` that finds no counterexample shows the claim within that scope only. A `run` asks for an instance, to show that a shape the check covers exists at all, so a check is not passing because nothing satisfies its premise. Each model restates the spec independently of clingo-i: it is the fifth oracle of Section 5.1. The search paid for itself: Section 7.1 lists what it found.

## 6. What runs, with numbers

Every command in `README.md` § Verify runs before each commit and again in CI on every push. On the author's machine, the clingo-i test suite takes about 50 seconds of wall time (about 400 seconds of CPU across cores), and `check_completion.py` takes 20 to 30 seconds.

### 6.1 The corpus

| Origin | Positive cases | Scenarios | Negative cases | Scenarios with the origin's answer |
|---|---|---|---|---|
| RL2 | 49 | 203 | 0 | 110 |
| DPROD | 17 | 88 | 0 | 88 |
| due2 | 15 | 69 | 14 | 0 |
| FORCE | 14 | 43 | 7 | 43 |
| OVAL | 9 | 23 | 8 | 19 |
| W3C | 4 | 12 | 0 | 9 |
| **Total** | **108** | **438** | **29** | **269** |

A negative case is a policy that W1 must reject, with the expected rejection code. clingo-i passes 400 of the 438 scenarios and declines 38: 37 need duty recurrence, which clingo-i does not implement (#80), and 1 exceeds its `max_mixed` bound, which has no fallback. It fails none.

### 6.2 The checks

| Check | Risk it guards | Size of one run | Limit |
|---|---|---|---|
| `check_corpus.py` | A case with unnamed rules, unbound operands, a missing `why`, or a policy outside the admitted profile. A negative case rejected for the wrong reason | 137 cases (29 rejected as expected) and the vendored DPROD examples | Its rejections re-implement W1. Two implementations of one rule drifted once before (`decisions/0014`) |
| Origin answers | Silent divergence from external evaluators | 269 scenarios | External semantics are inputs, not truth (#63) |
| `check_odrl22.py` | A policy presented as ODRL 2.2 that violates the ODRL 2.2 information model | 141 policies (19 invalid as expected) | Checks structure, not meaning |
| clingo-i on the corpus | A hand-derived answer that is wrong, or a program that disagrees with it | 438 scenarios: 400 pass, 38 decline | Same author and same spec reading on both sides |
| Deleted-rule tests | A rule lost from the program yielding a verdict instead of an error | 6 deletions | Covers the six rules chosen |
| Brute-force differential | clingo-i disagreeing with the Python oracle | 4 × 400 rule draws, 4 × 300 duty draws | Shares the completion key and the generator |
| Bounded-exhaustive spaces | clingo-i disagreeing with the Python oracle on a shape the generators rarely reach | Every input of nine spaces: 6,126 at the PR bounds; 73,876 at the slow bounds, outside README § Verify | Small inputs only; shares the oracle |
| Enumeration against fixed solves | The choice rule admitting a model that is not a completion, or missing one | 4 × 150 draws, up to 6 variables | Small policies only |
| Mutants | Assertions too weak to see a named error class; a space that stops reaching one | 23 mutants, each run on the explicit examples and 100 draws, and, at the slow bounds, on its space alone | Section 5.4 |
| Shape tallies | The generator never producing a hard shape | 21 shapes, 1,400 fixed-seed draws | At least one each, not a share |
| Claims M and W over the spaces | The two-extremes computation of `due2-workflows.md` §6.4 disagreeing with every completion; a verdict that holds by cases without an `unresolved` unknown | Every space input, at both bounds | The oracle's semantics, which the differential ties to clingo-i's |
| `check_completion.py` | A flaw in the two-completions shortcut or the listed frontier | 4 phases of 50,000 cases and 1 of 1,000, fixed seeds | Abstract model, not clingo-i |
| Alloy models | A counterexample to claim K, M, F, W, or P | Every instance within each command's scope (Appendix A.17) | Outside README § Verify; scopes are small |
| Driver tests (`test_flatten.py`) | The RDF-to-facts driver changing meaning: triple order, blank-node labels, malformed input | 1,264 tests | |
| Value tests (`test_values.py`) | Wrong comparison of numbers, dates, and durations | 58 tests | |
| Program unit tests | A rule-level or duty-level behaviour wrong on a hand-picked input | 227 in `test_interpret.py`, 78 in `test_duty.py` | Hand-picked |
| Harness self-tests | The harness passing a broken backend or failing a correct one | 33 tests | |
| Document checks | A citation to a missing section or decision; an undocumented program relation | 283 in `test_doc_references.py`, 65 in `test_docs.py`, strict MkDocs build | |
| Static checks | Type errors, lint, Markdown style | basedpyright (strict), ruff, rumdl | |

In all: 324 tests at the top level, 1,782 in clingo-i, and the 438 corpus scenarios through clingo-i, about 2,550 pytest items; `uv run pytest -m slow` adds 72 more in clingo-i. One clingo-i run generates 3,400 random cases for the differential and enumeration tests, plus up to 2,300 for the mutant kills and 1,400 for the shape tallies, and checks the 6,126 inputs of the PR spaces.

## 7. Assessment

### 7.1 What is good

- **The tests target named risks.** `correctness-strategy.md` lists the risks, and each check states which risk it guards and what would get through without it. That is the opposite of coverage chasing.
- **The oracles' overlaps are written down.** Section 5.1's table comes from the repository's own statements, not from this briefing. Knowing what an oracle shares is what lets you judge what its agreement means.
- **The tests themselves are tested.** Mutants check that the assertions can see each error class. Shape tallies check that the generator reaches the hard cases. Deleted-rule tests check that a missing rule fails loudly.
- **Disagreements with outside evaluators are kept and explained.** 269 scenarios carry the origin's own answer beside due2's, and the comparison found real upstream defects (Appendix A.2).
- **The oracle has already corrected the hand derivations.** The journal records corpus answers that clingo-i showed to be wrong (Appendix A.4).
- **The search before proof found real flaws.** The Alloy models found two, each now fixed in the spec, and neither visible to clingo-i's tests, because clingo-i and its oracle share the reading that was wrong:
  - *The completion key* (`decisions/0023`). ODRL lets two operands read one property, one with a concept scheme, where `eq` means "is the concept or a narrower one", and one without, where `eq` means identity. The key treated `isNoneOf c` on the one and `isAnyOf c` on the other as complements, one variable read with both polarities, though a concept below `c` makes both false. A definite verdict could rest on that pairing and be wrong. The key now includes whether the operand has a scheme.
  - *The listed frontier's fallback.* Beyond a bound on unknowns, W3 lists a cheaper approximation of the frontier. As first drafted for `decisions/0026`, under the `invalid` conflict strategy it could list a route that some completion removes. The fallback now leaves such candidates out (Appendix A.17).
- **The search also settled an open question.** The P model characterised when the earlier listed frontier omits a route, which made the choice in `decisions/0026` concrete (Section 3.1).

### 7.2 What is missing

1. **No evaluator exists.** Everything above checks the spec and its executable reading. Performance, memory, latency, and the production code's own bugs are untested because there is nothing to test.
2. **Duty recurrence is not executed.** 37 of the 38 declines need it (#80). `check_completion.py` excludes it as well.
3. **The laws L1 to L10 have no property tests.** `due2-workflows.md` §8 states them: determinism, information monotonicity, atomisation soundness, and the rest. The tier table in `correctness-strategy.md` puts them in the PR tier with Hypothesis's `fast` profile. No Hypothesis profile is registered yet.
4. **The bounded-exhaustive spaces are small, and their slow bounds run by hand.** A space covers up to two or three rules, trees of up to four to eight nodes, and two or three duties (`spikes/clingo-i/TESTS.md`). A defect that needs more stays a matter for random generation. The slow bounds, and the Alloy models, belong to a slow tier that CI does not run yet (`correctness-strategy.md` §7).
5. **The formal claims have bounded evidence, and no proof** (`correctness-strategy.md` §4.8):
   - M, monotonicity: a proof by cases in the spec; three phases of 50,000 random cases on the abstract model; every input of the slow spaces, 25,070 of them with a variable that moves the verdict both ways; and the Alloy model at scope 8.
   - K, the completion key: argued; the Alloy models at scope 6, after the gap of Section 7.1. The brute-force differential shares the key, so it is no evidence for it. The key is incomplete by design (`x ≤ 5` and `x > 7` stay independent, #25). The models check that this costs a needless `Indeterminate` only, never a wrong verdict.
   - F, frontier relevance: 942 definite `Pending` cases out of 50,000 on the abstract model, and the Alloy model at scope 6.
   - W, the basis waiver: 67 inputs of the slow spaces, and the Alloy model over every completion of three unknowns.
   - P, the listed frontier: the argument in `decisions/0026`; the abstract model's fifth phase, where the bounded computation equals brute force in all 942 definite `Pending` cases and the fallback lists no route that does not suffice in 148; and the Alloy model over every completion of three unknowns.

   A scope is a small bound, and the abstract model is not clingo-i. The prover spike on M was the next step; Section 8 has the revised sequence.
6. **The negative cases are checked only by `check_corpus.py`**, a second implementation of W1's rejections, until W1 exists.
7. **Common mode.** One author derived the expected answers, wrote clingo-i, and wrote the Python oracle, from one reading of the spec. External answers are the only independent check, and adequacy cannot be proved (`decisions/0021` #6).
8. **The ledger's stateful test is designed, not built** (`correctness-strategy.md` §4.7). Every test today evaluates one frozen snapshot.
9. **The PR gate is not deterministic.** `ways-of-working.md` §8's hard rule for the PR tier is "same commit, same result, always". In `spikes/clingo-i/tests/test_brute_force.py`, the rule and duty differentials (400 and 300 draws per copy) and the enumeration test (150 draws) fix no seed, so each CI run tests different cases. A failure would surface on whichever commit drew the failing case, not on the commit that introduced the bug, and a re-run could pass. Section 5.5 shows how far a single seed's results can move. The PR spaces are deterministic, which narrows the gap without closing it.
10. **clingo-i lags the spec on the listed frontier** (#103). It lists the frontier of the earlier rule. No corpus case reaches a shape where the two differ (`decisions/0026`), so the corpus does not show it.

### 7.3 Three things that look redundant and are not

Three parts of the setup are easy to mistake for waste. None is, but two point at real work:

- **`check_completion.py` on every commit.** There is no pre-commit hook. `ways-of-working.md` rules out tests in pre-commit, because a slow hook gets bypassed. The script runs as part of `README.md` § Verify. Its seeds are fixed, so re-running it on unchanged inputs repeats the same 201,000 cases. Moving it to a CI job that runs when `tools/check_completion.py` or `due2-workflows.md` §6.4 changes would save 20 to 30 seconds per commit and lose nothing. That is a suggestion for the author, not a decided item.
- **The abstract model beside clingo-i.** It is a second, much simpler restatement of the algorithm, so it catches a flaw in the algorithm that clingo-i would faithfully copy. Its risk is false confidence, and Section 5.2 is the remedy: say what the model omits wherever its numbers appear.
- **`COPIES = 4` in the brute-force tests.** The four copies have different random seeds, so they are four times the draws, not the same draws four times. They exist so pytest-xdist can run them in parallel (#82). The real gap is the missing tier profiles (7.2, items 3 and 9): with them, the copies would take fixed seeds in the PR gate and fresh ones in the slow tier.

## 8. Recommendations

Later on the day of this briefing's commit, the owner took two decisions that change the sequence, and this section was revised to follow them. The prover spike is parked until the evaluator reaches production (`decisions/0021`, the amendment of 2026-10-24). W1 stays Python, the corpus is the only thing that crosses from W1 to W2 and W3, and the bakeoff of `decisions/0006` ends without being run (`decisions/0027`). The W2/W3 language is open, with Kotlin leading (#104).

The first four follow the repository's own sequence, in its order: `CLAUDE.md` § Next for the first three, and `correctness-strategy.md` §8 for the ledger. The 10-21 briefing's first two, the enumerator and the search per claim, are done (Section 0). The last four are suggestions this briefing adds.

1. **Build the W2/W3 evaluator** (`decisions/0027`; its language is #104): relation-level vectors (#36, #37), the brute-force W3 (#38), then the evaluator as a spike under the shared suite, gated by `decisions/0006` #4. Agents as well as people will call it, so record the `ways-of-working.md` §10.4 measurables for that workload before any performance work.
2. **Build W1 in Python**: stage 1 with the Python `Den` oracle, then stage 2, gated by L9 against clingo-i. The 29 negative cases then get a real implementation instead of `check_corpus.py`'s.
3. **Finish the documentation house-cleaning** (#83), interleaved with the two above. Two points that writing this briefing found belong there. `due2-workflows.md` §1 and §6.4 give a frontier to `Pending` only, and do not say whether an `Indeterminate` reply lists one. And "open" has two senses: a precondition duty that is owed and not fulfilled (`due2-workflows.md` §6.1), and a route that a candidate gives in a completion (`decisions/0026`).
4. **Build the ledger**, gated by its stateful machine (`correctness-strategy.md` §4.7).
5. **Bring clingo-i to `decisions/0026`** (#103), so that the oracle lists the frontier the spec defines, and add recurrence (#80), which 37 of the 38 declines need.
6. **Register the Hypothesis profiles** (`fast`, `nightly`) and the slow tier that `correctness-strategy.md` already describes. Put the slow spaces and the Alloy models in it, write the L1–L10 property tests into it, and give the PR differentials fixed seeds (Section 7.2, item 9).
7. **Keep generator strength measured.** `test_spaces_alone_expose_mutant` now fails if the spaces stop exposing a mutant, so a planted bug no longer depends on a lucky seed. Random generation still matters beyond the spaces' bounds: re-measure Section 5.5's table with `tests/measure_mutants.py` whenever a generator changes.
8. **Get an outside reader for the spec.** Common mode (Section 7.2, item 7) is the largest risk no tool removes. A second person deriving a sample of corpus answers from the spec alone would test it directly.

---

## Appendix A: each check, with a real example

### A.1 Negative cases and `check_corpus.py`

**Risk.** A policy due2 must reject is accepted, or is rejected for an unrelated reason, so the case passes while testing nothing.

**Example.** `conformance/cases/due2-witness-outside-duty/policy.ttl` is valid ODRL 2.2, so its `case.json` has `"odrl22_valid": true`. due2 still rejects it:

```turtle
ex:stream a odrl:Permission ;
    odrl:action odrl:play ;
    odrl:target ex:album ;
    odrl:assignee ex:alice ;
    odrl:constraint ex:paid .

ex:paid a odrl:Constraint ;
    odrl:leftOperand odrl:payAmount ;
    odrl:operator odrl:gteq ;
    odrl:rightOperand "5.0"^^xsd:decimal .
```

due2's core profile binds `odrl:payAmount` to the witness source: it reads the payment recorded as evidence of a performed duty. A permission has no witness, so the constraint has nothing to read. The case expects `WitnessOutsideDuty`, and its `why` says: "Only a duty has a witness (workflows §5.2, §5.3), so W1 rejects the policy in stage 2." The real checker output:

```text
rej   due2-witness-outside-duty
      rejected, as expected: ex:paid: witness-source operand odrl:payAmount outside a duty [WitnessOutsideDuty]
```

The checker compares the code, not just the fact of rejection, so a policy rejected for some other reason fails the case. W1 does not exist, so this is `check_corpus.py`'s re-implementation of the rule (Section 7.2, item 6).

### A.2 Origin answers side by side

**Risk.** due2 drifts from what established evaluators answer, without anyone deciding that it should.

**Example.** `rl2-attestation-gating`, scenario "before the window opens", carries `"rl2_expected": "NotApplicable"`, while due2 expects `Pending`. The case's `notes` explain the difference: "before the window opens, RL2 reports the duty Pending and the decision NotApplicable; due2 reports the route, Pending with the attestation outstanding, and the obligation outstanding." Appendix C.2 shows the reply.

The comparison also works the other way. Importing external suites exposed defects upstream: OVAL fails open on purpose hierarchies (reported as DIPS-Tools/ODRL-Engine#8, due2 #52, still open), and OVAL mishandled null matching inside logical constraints (ODRL-Engine#9, fixed upstream). FORCE's policies 1 to 7 omit their targets (A.3).

### A.3 ODRL 2.2 validity with SHACL

**Risk.** A policy presented as ODRL 2.2 is not.

**Example.** `conformance/cases/force-01` is FORCE's first policy, imported unmodified. Its whole rule is:

```turtle
<urn:uuid:72e248bf-5f4f-472f-af76-8beca297415c> a odrl:Permission.
```

with the policy description "Everybody can do everything." The ODRL information model requires each rule to have an action and a target, either its own or inherited from the policy. `check_odrl22.py` reports two violations, one per missing property:

```text
Focus=urn:uuid:72e248bf-5f4f-472f-af76-8beca297415c | Path=- | OrConstraintComponent | Msg=Node <urn:uuid:72e248bf-5f4f-472f-af76-8beca297415c> must conform to one or more shapes in [ sh:property [ sh:minCount Literal("1", datatype=xsd:integer) ; sh:path odrl:action ] ] , [ sh:property [ sh:minCount Literal("1", datatype=xsd:integer) ; sh:path ( [ sh:inversePath [ sh:alternativePath ( odrl:permission odrl:prohibition odrl:obligation ) ] ] odrl:action ) ] ]
Focus=urn:uuid:72e248bf-5f4f-472f-af76-8beca297415c | Path=- | OrConstraintComponent | Msg=Node <urn:uuid:72e248bf-5f4f-472f-af76-8beca297415c> must conform to one or more shapes in [ sh:property [ sh:minCount Literal("1", datatype=xsd:integer) ; sh:path odrl:target ] ] , [ sh:property [ sh:minCount Literal("1", datatype=xsd:integer) ; sh:path ( [ sh:inversePath [ sh:alternativePath ( odrl:permission odrl:prohibition odrl:obligation ) ] ] odrl:target ) ] ]
```

The case says `"odrl22_valid": false`, so the run prints `xfail ... (odrl22_valid: false; 2 violations)` and passes. If the policy ever validated, the case would fail.

### A.4 The oracle correcting a hand derivation

**Risk.** A wrong expected answer becomes the standard every implementation is held to.

**Example.** The journal, `spikes/clingo-i/journal.jsonl`, 2026-10-18, case `dprod-audit-logs`, scenario "export the audit logs":

> Corpus error found once u duty findings stopped declining: the expected answer said the retention obligation was not in force because no rule matched an export, but rule:audit-no-export matches, so in_force rests on the obligation's guard, which reads a retention period the request does not state. in_force is u: the obligation is listed unknown with ex:retentionPeriod missing; the verdict stays Deny. The decline 'duty: unknown finding' had kept the vector from being checked.

Two lessons. The oracle caught a human error that a reviewer had missed. And a decline hid the error until the feature was implemented: a declined scenario is untested, not passed.

### A.5 A deleted rule fails loudly

**Risk.** A rule lost from the program, through an edit or a merge, produces a plausible verdict instead of an error.

**How.** The program states integrity constraints that every answer must satisfy. From `integrity.lp`:

```prolog
:- item(I), #count { V : holds(I, V) } != 1.
:- holds(_, V), not rank(V, _).
:- world(W), var(L), #count { V : assigned(W, L, V) } != 1.
```

Every item has exactly one truth value, every truth value has a rank, and every variable has exactly one value in each world. A program that breaks one has no answer set, and clingo-i reports an error. `test_deleted_rule_fails_loudly` in `spikes/clingo-i/tests/test_interpret.py` deletes each of four rules in turn, including `rank(u, 1).` from `kleene.lp`, runs a request that needs it, and asserts `"error" in reply`. Its comment says why each request exercises its rule: "an absent assignee gives a u part (kleene.lp), which is opaque, so its atom's finding takes the value of the atom's own variable (completion.lp)". `test_deleted_constraint_rule_fails_loudly` does the same for two constraint rules, one in `compare.lp` and one in `operand.lp`, and first checks that the intact program gives a definite verdict on its request, so only the deletion can turn the reply into an error.

### A.6 The brute-force differential

**Risk.** clingo-i's program, written as answer set rules, computes something other than the spec's definition.

**How.** `test_brute_force.py` generates random policies with nested `and`, `or`, `xone`, and `dprod:not` constraints, absent request fields, and unresolved state facts. A Python oracle evaluates each by brute force: it enumerates every completion and takes the verdicts directly from the definition. The test compares clingo-i's whole reply with the oracle's (verdict, basis, eliminated, unknown parts, verdict range), except the frontier, obligations, and `exact`, which the duty differential covers. First, `check_waiver` checks claim W on every reply (`correctness-strategy.md` §4.8): a definite `Permit` or `Deny` with an empty basis, which holds by cases over the completions, must list an `unresolved` unknown part. That is the premise under which `check_corpus.py` waives the basis check:

```python
def check(interp: Interpreter, case: Case) -> None:
    reply = interp.reply(render(case))
    got = reply.get("output")
    if isinstance(got, dict):
        check_waiver(got)
        reply = {
            "output": {
                k: v for k, v in got.items() if k not in ("frontier", "obligations", "exact")
            }
        }
    assert reply == oracle(case)
```

When the comparison fails, Hypothesis shrinks the input to a small failing case. Appendix C.3 shows one.

### A.7 Enumeration against fixed solves

**Risk.** clingo-i's choice rule, which makes clingo enumerate the completions, admits a model that is not a completion or misses one. The differential would not notice if the Python oracle had the same mistake.

**How.** The choice rule is:

```prolog
{ assigned(c, L, t); assigned(c, L, f) } = 1 :- var(L).
```

`test_enumeration_matches_fixed_solves` takes a generated policy with at most 6 variables and checks that the choice rule yields exactly 2ⁿ answer sets. It then deletes the choice rule and solves once per assignment, with each variable fixed by a fact, and checks that each fixed solve has exactly one model and that the two collections are equal. Finally it checks that the reply is `Indeterminate` exactly when the fixed solves disagree on the verdict, and that clingo's cautious result equals the intersection of the fixed solves:

```python
assume(len(variables) <= 6)
enumerated = shown_sets(text + "\n" + program)
assert len(enumerated) == 2 ** len(variables)
...
assert sorted(map(sorted, enumerated)) == sorted(map(sorted, solves))
common = solves[0].intersection(*solves[1:])
verdicts = {a for s in solves for a in s if a.startswith("verdict(")}
...
assert (out["verdict"] == "Indeterminate") == (len(verdicts) > 1)
assert shown_sets(text + "\n" + program, "cautious")[-1] == common
```

### A.8 Mutants

**Risk.** The differential's comparison is too weak to see a class of error. Section 5.4 explains what the kills do and do not mean, and Section 5.5 gives the table.

**How.** Each mutant is a text edit to one program file. `opaque-leaf-as-f` changes the rank of an opaque leaf from 1 (`u`) to 0 (`f`):

```python
"opaque-leaf-as-f": (
    "completion.lp",
    [("crank(W, C, 1) :- world(W), open(C), opaque_leaf(C).",
      "crank(W, C, 0) :- world(W), open(C), opaque_leaf(C).")],
),
```

`test_differential_kills_mutant` applies the edit, runs the differential on the explicit examples and then 100 generated draws, and passes only if the differential fails. Appendix C.3 walks this mutant's shrunk failing case.

### A.9 Shape tallies

**Risk.** Random tests pass because the generator never produces the hard cases (risk R9 in `correctness-strategy.md`).

**How.** `test_generator_reaches_each_shape` draws 400 cases with a fixed seed, counts the shapes, and fails if any wanted shape has a count of zero:

```python
WANTED = {f"conflict {c}" for c in ("prohibit", "perm", "invalid")} | {
    "open leaves reading one variable with both polarities",
    "Indeterminate with a non-pivotal u atom",
    "two u atoms sharing a variable",
    "an atom with a variable of its own",
    "an open tree with an opaque and a paired leaf",
    "an f atom on an absent target",
    "constraint parts sharing a key",
    "u leaf under a deciding connective",
    "u leaf that only f atoms read",
}


def test_generator_reaches_each_shape() -> None:
    seen: Counter[str] = Counter()

    @settings(max_examples=400, deadline=None, database=None, derandomize=True)
    @given(cases(dead=True))
    def tally(case: Case) -> None:
        seen.update(shapes(case))

    tally()
    assert {s: seen[s] for s in WANTED if seen[s] == 0} == {}, seen
```

A non-pivotal unknown is one that cannot change the verdict, like the `u` in `T or u`. If the generator never produced one, nothing would test that the reply leaves such unknowns unnamed. `test_duty_generator_reaches_each_shape` does the same for 9 duty shapes over 1,000 draws.

### A.10 The two-completions shortcut, against brute force

**Risk.** The monotonicity proof (claim M) or the frontier argument (claim F) is wrong, so the shortcut gives a definite verdict that some completion contradicts.

**How.** `tools/check_completion.py` generates small problems on an abstract model (one policy, flat conjunctions, no recurrence or instances) and compares the shortcut with brute force over every completion. Its docstring calls it "A sanity check of §6.4's claims, not a proof". The real output:

```text
50000 cases, 0 mismatches; definite under v0.6, Indeterminate before: 1244
1000 wide cases, 0 unsound; fallback in 111, Indeterminate there where the exact reading decides: 84
50000 guarded-duty cases, 0 mismatches; a guard variable mixed in 24553
50000 deadline/violations cases, 0 mismatches; Deny under violations = deny in 3285
50000 partial-knowledge cases, definite Pending in 942: listed frontier empty in 1 (v0.33: 191; routes open in every completion: 181); differs from v0.33's in 191; v0.33 listed a route that does not suffice in 0; frontier_complete false in 189, true where an uncertain candidate exists in 143; bounded enumeration 0 mismatches; with bound 1, fallback in 148, 0 unsound
```

Phases 1, 3, and 4 are the evidence for M. Phase 5 is the evidence for F and P. It computes the listed frontier of `decisions/0026` by brute force over every completion, and compares three readings on the same 942 definite `Pending` verdicts: the decided one leaves the requester with nothing to do once, `due2-workflows.md` v0.33's rule 191 times, and "the routes open in every completion" 181 times. "`frontier_complete` false in 189" counts the verdicts where some completion's frontier differs from the listed one, and "true where an uncertain candidate exists in 143" counts those where enumeration proves the frontier complete although the cheaper rule of `decisions/0004`, complete only when no candidate is uncertain, would say it is not. "Bounded enumeration 0 mismatches" says the computation over the relevant unknowns equals brute force. "With bound 1, fallback in 148, 0 unsound" forces the fallback beyond `max_frontier_vars` in 148 cases and finds it never lists a route that does not suffice. Section 5.2 says what "0 mismatches" supports.

### A.11 Driver invariance

**Risk.** The Python driver that turns RDF into solver facts changes meaning with triple order or blank-node labels.

**How.** `test_graph_invariance` in `spikes/clingo-i/tests/test_flatten.py` serialises each policy to N-Triples, relabels it randomly, and checks that the facts are unchanged:

```python
def test_graph_invariance(path: Path, rnd: random.Random) -> None:
    text_ = path.read_text()
    g = exact_graph(path)
    assert g is not None
    saved, rdflib.NORMALIZE_LITERALS = rdflib.NORMALIZE_LITERALS, False
    try:
        nt = g.serialize(format="nt")
    finally:
        rdflib.NORMALIZE_LITERALS = saved
    a = set(flatten.policy_facts(flatten.parse(text_)))
    b = set(flatten.policy_facts(flatten.parse(relabel(nt, rnd))))
    assert a == b
```

### A.12 Exact ordering across value spaces

**Risk.** Comparing numbers, instants, and durations goes wrong through rounding, time zones, or integer overflow in the solver.

**How.** The solver compares integers only, so the driver maps each value to an exact rank. `test_values.py` checks the arithmetic against Python's own. `test_daytime_sum` adds a day-time duration to an instant both ways:

```python
def test_daytime_sum(dt: datetime, n: int) -> None:
    i = date_time(instant_lex(dt, 6, zulu=True))
    d = duration(f"{'-' if n < 0 else ''}PT{abs(n)}S")
    assert isinstance(i, Instant) and d is not None
    assert add(i, d[0]) == seconds(dt + timedelta(seconds=n) - EPOCH)
```

`test_outside_int32_ranks` checks that values beyond the solver's 32-bit integers still rank correctly, by position rather than raw value.

### A.13 Harness self-tests

**Risk.** The test harness passes a broken backend or fails a correct one.

**How.** `tests/test_harness.py` runs the harness against fake backends in `tests/fixtures/`. For example, `test_empty_backend_fails_every_vector` checks that a backend that answers nothing fails every vector, and `test_missing_keys_and_non_objects_are_malformed` checks that a malformed reply is reported as malformed.

### A.14 Checker diagnostics

**Risk.** A negative SHACL case passes for the wrong reason.

**How.** `test_an_undefined_action_fails_the_rule_and_the_class` in `tests/test_vocabulary.py` checks the specific violations, not just that the policy fails:

```python
found = problems("due2-undeclared-action", checker)
assert any("IM 2.1: <http://example.com/promote>" in p for p in found), found
assert any(is_action_class(p) for p in found), found
```

Its docstring states the counterfactual: before `decisions/0020`, "an action from no vocabulary passed".

### A.15 Document checks

**Risk.** Documents cite sections or decisions that do not exist, or a program relation has no documentation.

**How.** `test_every_cited_decision_exists` in `tests/test_doc_references.py` collects every `decisions/NNNN` citation in a file and asserts that each record exists. `spikes/clingo-i/tests/test_docs.py` checks that each program relation has one doc block and that each file's header lists what it consumes and provides.

### A.16 Static checks

basedpyright in strict mode, ruff, and rumdl run over both Python projects and all Markdown. The repository has no `type: ignore` comments.

### A.17 Alloy models

**Risk.** A claim of `correctness-strategy.md` §4.8 is false, and clingo-i and its Python oracle share the mistake, so the differential cannot see it.

**How.** Each claim gets a small model in `formal/alloy/`, written from the spec's text, not from clingo-i. `resolve.als` states W3 over one completion: candidates, conflict, the frontier, and the verdict. Each claim's model quantifies over a set of worlds, the completions. Alloy searches every instance up to a *scope*, a bound on the size of each signature. A `check` asserts a claim, and prints `UNSAT` when no instance within the scope contradicts it. A `run` asks for an instance, and prints `SAT` when one exists. Some runs are witnesses that a check is not vacuous: its premise can hold. Others pin a known gap. The real output of `formal/alloy/run.sh` at `c711e89`, for P; each line is Alloy's own, the command's number, kind, and name, then its outcome:

```text
p_listed_frontier
00. run   NoSingleGiver            0    1/1     SAT
01. run   OpenInSome               0    1/1     SAT
02. run   DominatedInSome          0    1/1     SAT
03. run   EmptyListed              0    1/1     SAT
04. run   InvalidNeedsExclusion     0    1/1     SAT
05. check NoOmission               0       UNSAT
06. check PermitListsEmpty         0       UNSAT
07. check FallbackSound            0       UNSAT
```

`NoOmission` says that a route every completion's frontier offers is listed, which is the omission `decisions/0019` found in the earlier rule. `FallbackSound` says every candidate the fallback lists survives in every completion. `InvalidNeedsExclusion` is the flaw of Section 7.1: drop the exclusion of candidates whose policy is under `invalid` with a `U` prohibition, and an instance exists where the fallback lists a candidate that some completion removes. The P checks run over 8 worlds, every completion of three unknowns.

The whole run, every model, took 3 min 27 s on a 10-core Mac when measured for this briefing. Every check printed `UNSAT` and every run its expected outcome. `formal/alloy/README.md` lists each command's scope, expected outcome, and time. `run SchemeGap` in `k_completion_key.als` pins the other flaw of Section 7.1: under the completion key before `decisions/0023`, two leaves it pairs as complements are both false on one value.

A scope is not a proof. A counterexample that needs four unknowns or four permissions is outside these bounds. `resolve.als` leaves out recurring instances, deadlines as findings, the non-default combinations, and grounds, and its header argues why none weakens the models.

---

## Appendix B: how unknowns are handled

### B.1 Statuses

Every value the evaluator reads has a status (`due2-workflows.md` §3, §5.4):

| Status | Meaning | Completed or opaque |
|---|---|---|
| `resolved` | One value (or, for a set-valued operand, its members) | Not unknown, unless it does not fit the operator |
| `unresolved` | A lookup failed, or the state property has no fact | Completed |
| `missing` | A lookup found no value, or a request field is absent | Opaque |
| `invalid` | The value cannot be read as its declared type | Opaque |
| `conflict` | Two or more values for a single-valued property | Opaque |
| `misfit` | A `resolved` value that does not fit the operator, such as a day-time duration against a year-month one (Section 2), or a `dateTime` without a timezone (`decisions/0024`) | Opaque |

Any status but a fitting `resolved` value makes the part `U`. An opaque part is never paired with another part, because nothing says its input has one value that fits, so an operator and its complement need not have opposite truth values there (`decisions/0016`). In the anonymization case of Section 3, the fact is `missing`, so its part is opaque. The permission is `U`, and the permission's own finding is completed instead, which gives the range from `NotApplicable` to `Permit`.

One status is deliberately not unknown. Absent evidence of a duty means *not yet performed*, never unknown: "a duty with none is outstanding, and the requester is told so through `Pending`" (`due2-workflows.md` §5.3). Evidence arrives in the case history when it is submitted, so its absence is a fact about the case.

### B.2 Kleene logic in the program

`kleene.lp` ranks the truth values `rank(f, 0). rank(u, 1). rank(t, 2).` Conjunction takes the least rank and disjunction the greatest, so an unknown can pull a conjunction down to `u` but never to `f` on its own.

### B.3 Canonical literals

Two parts with the same key share a variable, and a complement shares it with the opposite polarity. In `completion.lp`, a leaf's value in world `W` is read from its literal's assignment, flipped for a negative polarity:

```prolog
crank(W, C, N) :- leaf_lit(C, L, pos), assigned(W, L, V), rank(V, N).
crank(W, C, 2 - N) :- leaf_lit(C, L, neg), assigned(W, L, V), rank(V, N).
```

Ranks run 0, 1, 2, so `2 - N` swaps `t` and `f`. If `x < 18` and `x >= 18` are one literal with opposite polarities, no world makes both true. Two of the mutants break exactly this: `variable-per-leaf` gives each leaf its own literal, and `polarity-ignored` drops the flip.

### B.4 Pivots: which unknowns an Indeterminate names

An `Indeterminate` names the unknowns that matter (`decisions/0011`). A variable is *pivotal* when flipping it alone, in some completion, changes the verdict. `pivot.lp` finds them with a second world that copies a completion and flips one chosen variable:

```prolog
world(flip).
{ pivot(L) : var(L) } = 1.
assigned(flip, L, V) :- assigned(c, L, V), not pivot(L).
assigned(flip, L, t) :- pivot(L), assigned(c, L, f).
assigned(flip, L, f) :- pivot(L), assigned(c, L, t).
:- verdict(c, Verdict), verdict(flip, Verdict).
unknown(X) :- reads(I, L), pivot(L), finding_atom(I, X).
```

The constraint discards every model where the flip leaves the verdict unchanged, so each surviving model has one pivot. A pivot is one variable, not a minimal set. The rules that read a pivot are reported with role `unknown`. The mutant `flip-constraint-deleted` removes the constraint, which makes every variable look pivotal.

### B.5 Duties under incomplete information

A duty has findings of its own (`due2-workflows.md` §5.1):

| Finding | For | `T` | `F` |
|---|---|---|---|
| `owed` | A precondition duty | Every guard holds | A guard fails |
| `in_force` | A root obligation | Its policy matches the request and its guards hold | Its policy does not match, or a guard fails |
| `fulfilled` | Either, when owed or in force | Some witness satisfies the duty | Every witness fails, or there is none |

Each is `U` otherwise. Duty status reuses the same values: `fulfilled` is `T`, `outstanding` is `F`, `unknown` is `U`. Timing adds `violated`, derived from the deadline, which is reported but does not enter Kleene combination. Appendix C.2 shows an outstanding duty, and the same case, once the deadline passes, a violated one.

---

## Appendix C: three answers and one planted bug, walked

Every reply below is clingo-i's output at `c711e89`, from a scratch script that loads the corpus with `tools/harness` and calls `Interpreter.reply`. The harness test `uv run pytest --backend=clingo-i` compares the same replies with the expected answers.

### C.1 Indeterminate: `rl2-anonymization-required`

The policy:

```turtle
ex:researchAgreement a odrl:Agreement ;
    odrl:profile <https://ekgf.org/dprod/spec/develop/> ;
    odrl:conflict odrl:prohibit ;
    odrl:assigner ex:Hospital ;
    odrl:assignee ex:ResearchInstitution ;
    odrl:permission ex:processAnonymizedData .

ex:processAnonymizedData a odrl:Permission ;
    odrl:action ex:process ;
    odrl:target ex:PatientDataset ;
    odrl:constraint [
        a odrl:Constraint ;
        odrl:leftOperand ex:anonymized ;
        odrl:operator odrl:eq ;
        odrl:rightOperand true
    ] .
```

`ex:anonymized` reads the state property `ex:targetAnonymizationApproved`, a boolean. The case has three scenarios:

| Scenario | The fact | Verdict | `unknown_parts` status | `verdict_range` |
|---|---|---|---|---|
| approved anonymization assessment | `resolved`, `true` | `Permit` | none | none |
| assessment missing | `missing` | `Indeterminate` | `missing` | `NotApplicable` to `Permit` |
| assessments disagree | `conflict`, `true` and `false` | `Indeterminate` | `conflict` | `NotApplicable` to `Permit` |

The full reply for "assessment missing" is in Section 3. In words: the permission's constraint is `U`, so the permission is `U`. If it applies, the verdict is `Permit`. If not, nothing applies, and the verdict is `NotApplicable`. The reply names the one input that would decide it. RL2 gives `Permit` for the first scenario and has no counterpart for the other two.

An evaluator that read the missing assessment as false would answer `NotApplicable`. The requester would be refused with no hint that an assessment is the missing piece. The `conflict` row matters more: two assessments that disagree are not a "no".

### C.2 Pending: `rl2-attestation-gating`

The policy grants read and export access, each with a precondition: the processor must attest conformance inside a window. The same duty is also a root obligation of the agreement.

```turtle
ex:readPrivilege a odrl:Permission ;
    odrl:action odrl:read ;
    odrl:duty ex:attestConformance .

ex:attestConformance a odrl:Duty ;
    odrl:assignee ex:DataProcessor ;
    odrl:assigner ex:Regulator ;
    odrl:action ex:attest ;
    odrl:target ex:GovernedDataset ;
    odrl:constraint [
        a odrl:Constraint ;
        odrl:leftOperand ex:performedAt ;
        odrl:operator odrl:gteq ;
        odrl:rightOperand "2026-01-01T00:00:00Z"^^xsd:dateTime
    ] ;
    dprod:deadline "2027-01-01T00:00:00Z"^^xsd:dateTime .
```

`ex:performedAt` reads `due2:actionTime`, the time the evidence says the attestation happened, so the constraint is a condition on the witness, not on the request.

Scenario "before the window opens": `ex:DataProcessor` requests `odrl:read` on `ex:GovernedDataset` at 2025-06-01, with no evidence. The reply:

```json
{
  "verdict": "Pending",
  "frontier": [["https://example.org/attestConformance"]],
  "obligations": [{"duty": "https://example.org/attestConformance", "status": "outstanding"}],
  "exact": true,
  "verdict_basis": [
    {"ref": "https://example.org/attestConformance", "role": "duty"},
    {"ref": "https://example.org/attestConformance", "role": "obligation"},
    {"ref": "https://example.org/readPrivilege", "role": "permission"}
  ],
  "eliminated": [],
  "unknown_parts": []
}
```

The frontier is a list of alternatives, each a set of duties. Here there is one alternative with one duty: perform the attestation and the read is permitted. RL2 answers `NotApplicable` for this scenario. Appendix A.2 quotes the case's explanation of the difference.

Scenario "window closed without attestation": the request comes after the deadline, still with no evidence. The duty instance is violated, and a violated precondition removes its candidate:

```json
{
  "verdict": "NotApplicable",
  "frontier": [],
  "obligations": [{"duty": "https://example.org/attestConformance", "status": "violated"}],
  "exact": true,
  "verdict_basis": [
    {"ref": "https://example.org/attestConformance", "role": "obligation"},
    {"ref": "https://example.org/readPrivilege", "role": "closed"}
  ],
  "eliminated": [
    {"ref": "https://example.org/readPrivilege", "by": "https://example.org/attestConformance", "rule": "violated_precondition"}
  ],
  "unknown_parts": []
}
```

Under the default `violations = ignore`, the violated obligation is reported but does not decide the verdict. The next scenario sets `violations = deny`, and the same input gives `Deny`.

### C.3 A planted bug caught: `opaque-leaf-as-f`

This mutant reads an opaque leaf as false: the classic "unknown means no" bug (A.8). Run against generated cases only, the differential first exposed it at draw 47 under seed 0, and as early as draw 3 under seed 4 (Section 5.5). `measure_mutants.py --shrink opaque-leaf-as-f` searches again, derandomized and with shrinking, and reduces the failing case to this policy, which `test_opaque_leaf_as_f_fails_open` pins:

```turtle
ex:p a odrl:Set ; odrl:conflict odrl:prohibit ; odrl:prohibition ex:r0 .
ex:r0 a odrl:Prohibition ; odrl:action odrl:use ; odrl:target ex:a ;
    odrl:constraint [ odrl:leftOperand ex:o0 ; odrl:operator odrl:eq ; odrl:rightOperand 1 ] .
ex:o0 dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:o0 .
```

The request asks to `odrl:use` something, but states neither the target nor the parameter `ex:o0`. (The shrunk vector also declares two unused operands, `ex:o1` and `ex:o2`, omitted here.) So the prohibition has two opaque `U` parts: the target, and the constraint.

The oracle's answer:

```json
{
  "verdict": "Indeterminate",
  "verdict_basis": [{"ref": "https://example.org/r0", "role": "unknown"}],
  "verdict_range": {"low": "Deny", "high": "NotApplicable"},
  "eliminated": [],
  "unknown_parts": [
    {"ref": "https://example.org/r0", "input": "http://www.w3.org/ns/odrl/2/target", "status": "missing"},
    {"ref": "https://example.org/r0", "input": "https://example.org/o0", "status": "missing"}
  ]
}
```

The mutant's answer, trimmed to the same fields:

```json
{
  "verdict": "NotApplicable",
  "verdict_basis": [],
  "eliminated": [],
  "unknown_parts": [
    {"ref": "https://example.org/r0", "input": "http://www.w3.org/ns/odrl/2/target", "status": "missing"},
    {"ref": "https://example.org/r0", "input": "https://example.org/o0", "status": "missing"}
  ]
}
```

With the leaves read as false, the prohibition cannot apply, so the mutant says `NotApplicable`. It still lists both unknowns, but its verdict ignores them. In a policy that also had a matching permission, the same bug would turn a possible `Deny` into a `Permit`: a request goes through because it left out the fact that would have blocked it. The differential compares whole replies, so the verdicts differ, the assertion fails, and the mutant is killed.

Not every kill looks like this. Under seed 0 the differential exposed `variable-per-leaf` at draw 12, and the shrunk case that `--shrink variable-per-leaf` finds makes the mutant fail one of the integrity constraints of A.5. clingo-i returned an error, not a wrong verdict. That also counts as a kill: the differential expects an output and gets an error. This shows A.5's design working: a broken program tends to fail loudly.

---

## Appendix D: sources for the statistics

- H. D. Mills, *On the Statistical Validation of Computer Programs*, IBM Federal Systems Division, report FSC-72-6015, 1972. Error seeding and the confidence formula.
- G. J. Myers, *The Art of Software Testing*, Wiley, 1979. States Mills' formula in the form used in Section 5.3.
- R. A. DeMillo, R. J. Lipton, and F. G. Sayward, "Hints on Test Data Selection: Help for the Practicing Programmer", *IEEE Computer* 11(4), 1978. Mutation testing and the coupling effect.
- R. Just, D. Jalali, L. Inozemtseva, M. D. Ernst, R. Holmes, and G. Fraser, "Are Mutants a Valid Substitute for Real Faults in Software Testing?", FSE 2014. When the coupling assumption holds.
- J. A. Hanley and A. Lippman-Hand, "If Nothing Goes Wrong, Is Everything All Right? Interpreting Zero Numerators", *JAMA* 249(13), 1983. The rule of three.
- D. Jackson, *Software Abstractions: Logic, Language, and Analysis*, MIT Press, 2006. The small-scope hypothesis and Alloy.
