# 0001 — due2 stays ODRL-native; RL2 is a donor; DPROD Contracts is a profile

**Status:** Decided, 2026-10-09
**Context documents:** `due2-architecture.md` §8.2–§8.3 · `due2-profiles.md` · `conformance/`

## Question

RL2 is more ambitious and more complete than due2's own specifications. Should due2 move to RL2 — adapted, with due2's work merged in — and proceed from there?

## Decision

1. **due2 stays ODRL 2.2-native.** Authors write ODRL. Extensions enter only as profiles, through the closed set of extension points in `due2-profiles.md` §2, declared as data and compiled mechanically.
2. **RL2 is a design source, not the language.** Its worked-out material is harvested (architecture §8.2). Its vocabulary is not adopted.
3. **RL2's use cases are kept, rewritten in ODRL.** All 49 are conformance cases (`conformance/cases/rl2-*`).
4. **DPROD Contracts is supported as a profile, as published.** Its operand bindings are due2's; its other terms land on due2's extension points. due2 refines DPROD's decisions, with six documented exceptions (`due2-profiles.md` §8.2).

## Why

A review of RL2 (October 2026) found:

- **It is not a superset of ODRL.** It has its own namespace and terms, and reaches ODRL only through a partial translator. That translator rejects ODRL's most common duty pattern unless configured otherwise, because it misreads the attached duty as ambiguous: ODRL defines it as a pre-condition. It also changes the meaning of `invalid`.
- **It has never been executed.** There is no evaluator and no compiler, and its vectors are prose. Its own backlog estimates 6–10 person-months to a conforming evaluator and importer, and its last architecture note keeps it off the critical path.
- **Its value is mostly evaluation semantics,** which transfers to due2 without the vocabulary.

The rewrite tested that claim directly:

| Origin | Cases | ODRL core | ODRL + profile | Partial | Not expressible | Scenarios |
|---|---|---|---|---|---|---|
| RL2 use cases | 49 | 35 | 2 | 8 | 4 | 203 |
| DPROD Contracts examples | 17 | 3 | 14 | — | — | 88 |

- **RL2.** 37 of 49 use cases are fully expressible in ODRL, with at most a profile term. Of the 110 scenarios that state an RL2 outcome, 104 get the same verdict in due2. The remaining 6 are standing divergences, mainly `Pending` with a route where RL2 says `NotApplicable`.
- **What ODRL plus due2 cannot express,** by theme:
  - the status of an obligation outside any matching request: 4 cases, waiting on the monitoring question;
  - Promises and Offer → Agreement materialisation: 3;
  - Maintain duties: 2;
  - duty status used as an operand: 2;
  - windows anchored to a snapshot fact: 2;
  - one case each for conflicting evidence records, direct-only collection membership, consequent duties, and a duty object bound to the requested asset.

  None of these is needed by a real policy yet.
- **DPROD.** All 16 policies in DPROD's example files pass the corpus checker unchanged, with the DPROD profile selected by their own `odrl:profile`; since 2026-10-10 the four example files are vendored unmodified under `profiles/vendor/dprod/examples/`, so this is reproducible locally, and all 16 policies are covered by corpus cases (`conformance/cases/dprod-*`, together with the constructed `dprod-divergences` and `dprod-not-negated-purpose`). Of the 88 scenarios that state a DPROD outcome, 66 agree. The other 22 fall under the six exceptions and DPROD's duty-collection rule: 10 are `Failure`-to-decision refinements (missing values that due2 completes rather than fails on), and 12 are verdict divergences — six of them a violated duty denying under `violations = deny` where DPROD never collects the duty for the requested action.

**Note (2026-10-18):** the counts above still hold, re-derived from the corpus's `dprod_expected` and `rl2_expected` at 126 cases, but the reason given for the 10 `Failure` scenarios is out of date. Since `decisions/0016`, due2 completes only an `unresolved` value, and a missing one is opaque. 7 of the 10 are `Indeterminate`, due2's counterpart of DPROD's `Failure`. In the other 3 the missing value cannot change the rule's finding under Kleene logic: F ∧ U = F twice (`NotApplicable`) and U ∨ T = T once (`Permit`).

## Consequences

- RL2's evaluation ideas are available to due2 without a second vocabulary or a translator to maintain.
- Constructs that are not expressible stay recorded in the corpus, so each can be revisited when a real policy needs it.
- The monitoring question — what a party owes now, independent of a request — is the gap with the most cases behind it (`due2-workflows.md` §9).
- Testing DPROD found gaps in DPROD itself: matching direction, order-dependent errors, unreachable rules, duty collection by action, and unbounded recurrence. They are listed for upstream in `due2-profiles.md` §8.2.

## Revisit when

- a real policy needs a construct the corpus marks not expressible; or
- a standards route opens for RL2's semantics, in which case the natural form is an ODRL profile plus an evaluation-semantics document, which is the shape due2 already has.
