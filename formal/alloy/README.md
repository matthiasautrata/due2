# Alloy models

Each claim of `correctness-strategy.md` §4.8 gets a small Alloy 6 model, which searches for a counterexample within a bound on the size of each signature (`decisions/0021`). A `check` that finds none shows the claim only up to that scope. A `run` shows that an instance exists, either a known gap or a witness that a check is not vacuous. A counterexample is triaged by `correctness-strategy.md` §6.

The models are not part of README § Verify. They belong to the slow tier (`correctness-strategy.md` §7), which does not exist yet. Run them with

```bash
formal/alloy/run.sh                          # every model
formal/alloy/run.sh formal/alloy/<model>.als # one model
```

The script needs Java 17 or later. It runs Alloy 6.2.0, the Maven artifact `org.alloytools:org.alloytools.alloy.dist`, and checks the jar against the SHA-256 digest pinned in `run.sh`. It uses the jar in the local Maven repository (`~/.m2`) if there is one there. Otherwise it downloads the jar once into `~/.cache/due2/`, from Maven Central or from the repository named by `DUE2_MAVEN_REPO`, such as a mirror of Maven Central. Credentials for the download go in `~/.netrc`. Where only Maven can reach the mirror, run `mvn dependency:get -Dartifact=org.alloytools:org.alloytools.alloy.dist:6.2.0` first. Each command prints one line with its outcome: a `check` should print `UNSAT` (no counterexample), and a `run` prints `SAT` when it finds an instance.

## Models

| Model | Claim | Spec sections |
|---|---|---|
| `k_completion_key.als` | K: the completion key is sound, and one-sided at the leaves | `due2-workflows.md` §5.4, §6.4; `due2-profiles.md` §3, §4; `decisions/0012`, `0015`, `0016`, `0023` |
| `kleene_regularity.als` | The connectives are regular, which carries K's one-sidedness from the leaves to the findings | `due2-workflows.md` §5.2; `decisions/0016` |
| `resolve.als` | None: a module, W3 over one completion, opened by the four models below | `due2-workflows.md` §6.1–§6.4 |
| `m_monotonicity.als` | M: the verdict is monotone in every finding, and the uniform variables are bounded by the two extremes | `due2-workflows.md` §6.4 |
| `f_frontier_relevance.als` | F: two `Pending` completions that agree on the relevant unknowns have one frontier | `due2-workflows.md` §6.4; `decisions/0004` |
| `w_basis_waiver.als` | W: a definite `Permit` or `Deny` with an empty basis has a `U` finding on a variable that another literal reads too | `due2-workflows.md` §6.4; `decisions/0016` |
| `p_listed_frontier.als` | P, a question: the shapes in which the listed frontier omits a route that every completion offers | `due2-workflows.md` §6.3, §6.4; `decisions/0019` |

`resolve.als` leaves out instances, timing, the non-default combinations, and grounds; its header gives the reason for each. A model that quantifies over every completion asserts `everyCompletion`: the worlds are closed under flipping one variable, and no two are one completion. Its scope on `World` therefore bounds the unknowns, variables and unknown `fulfilled` findings together: 8 worlds hold every completion of three. At scope 3 there are at most three variables, so a fourth unknown is an unknown `fulfilled` finding.

## Scopes and times

Measured on 2026-10-23 (K) and 2026-10-24 (M, F, W, P) with Alloy 6.2.0, its default SAT4J solver, and Java 27 on an arm64 Mac, one command at a time. The scope bounds every signature; `3, 8 worlds` is `for 3 but 8 World`.

| Model | Command | Scope | Expected | Outcome | Time |
|---|---|---|---|---|---|
| `kleene_regularity.als` | `check Regular` | 7 | no counterexample | none | 9 s |
| | `run XoneDecidedOverU` | 4 | an instance | found | under 1 s |
| `k_completion_key.als` | `check KeyIsEquivalence` | 6 | no counterexample | none | 2 s |
| | `check KeySound` | 6 | no counterexample | none | under 1 s |
| | `check OneSidedAtLeaves` | 6 | no counterexample | none | 65 s |
| | `run SchemeGap` | 3 | an instance: the key before `decisions/0023` is unsound | found | under 1 s |
| | `run Issue25BothT` | 4 | an instance: #25's gap | found | 1 s |
| | `run Issue25BothF` | 4 | none: the gap as `decisions/0021` states it is not one | none | under 1 s |
| | `run MisfitBreaksPairing` | 3 | an instance (`decisions/0016`) | found | 1 s |
| | `run ComplementPair` | 4 | an instance | found | under 1 s |
| `m_monotonicity.als` | `check Monotone` | 8 | no counterexample | none | 9 s |
| | `check UniformBound` | 7 | no counterexample | none | 3 s |
| | `run MonotoneStrict` | 3 | an instance: `Deny` below `Permit`, under `invalid` | found | under 1 s |
| | `run MixedVariable` | 3 | an instance: a mixed variable whose extremes disagree | found | 1 s |
| `f_frontier_relevance.als` | `check Relevant` | 6 | no counterexample | none | 3 s |
| | `run RelevantMoves` | 3 | an instance | found | 1 s |
| | `run IrrelevantDiffers` | 3 | an instance | found | under 1 s |
| `w_basis_waiver.als` | `check Waiver` | 3, 8 worlds | no counterexample | none | 109 s |
| | `run EmptyPermit` | 3, 4 worlds | an instance | found | 1 s |
| | `run EmptyDeny` | 3, 4 worlds | an instance | found | under 1 s |
| `p_listed_frontier.als` | `check ListedGiver` | 3, 8 worlds | no counterexample | none | 9 s |
| | `check Flagged` | 3, 8 worlds | no counterexample | none | 1 s |
| | `check NeedsMixed` | 3, 8 worlds | no counterexample | none | 483 s with glucose |
| | `check TwoRoutes` | 3, 8 worlds | no counterexample | none | 591 s with glucose |
| | `run Shape0019` | 3, 4 worlds | an instance | found | 1 s |
| | `run ClosingPrecondition` | 3, 4 worlds | an instance | found | under 1 s |
| | `run ComplementaryPreconditions` | 3, 4 worlds | an instance | found | 1 s |
| | `run SelfContradiction` | 3, 4 worlds | an instance | found | under 1 s |

One-sidedness checked in one model, leaves and connectives together, did not finish in five minutes even at scope 3, so it is split into `OneSidedAtLeaves` and `Regular`.

The checks that quantify over every completion grow fast with the worlds. `everyCompletion`'s rule that no two worlds are one completion spares the solver their permutations: before it, `check Waiver` at 8 worlds did not finish in ten minutes. The native solver glucose is often faster than SAT4J (`DUE2_ALLOY_SOLVER=glucose`): `check Waiver` takes 50 s with it, P's two slowest checks are timed with it, and at 16 worlds, every completion of four, it finds no counterexample in 13 minutes.

## Findings

Each counterexample is triaged by `correctness-strategy.md` §6.

- **W, an overflow.** A `check Waiver` that counts the literals reading a variable with Alloy's integers finds a false counterexample: their default width of 4 bits wraps a count of 8 to −8. The error is the model's, so `readTwice` states "read twice" without arithmetic, and the check finds no counterexample.
- **P, the omission's shapes.** P is a question, so its counterexamples are its answer. A route is a permission's outstanding set, the duties still to do on it (`due2-workflows.md` §6.1), and an omission is a definite `Pending` with a route that every completion's frontier offers and the listed frontier lacks. At 8 worlds:
  - Every omission makes some completion's frontier differ from the listed one (`Flagged`), so `frontier_complete` is false (`due2-workflows.md` §6.4: true iff each assignment yields the listed frontier). The reply is flagged incomplete, never silently wrong.
  - Every omission needs a mixed variable, one read upward and downward (`due2-workflows.md` §6.4, *Computing it*; `NeedsMixed`).
  - A route that one permission gives in every completion is listed (`ListedGiver`), unless a finding reads a variable both ways, such as `x eq 5` and `x neq 5` in one `and`, which is `U` before completion and `F` in every completion (`SelfContradiction`).
  - Without such a finding, an omission needs two permissions that both read one mixed variable, in their own findings or their preconditions' `owed` (`TwoRoutes`). So prohibitions, `fulfilled` findings, and obligations alone never cause one.

  Four shapes reach it, one run each: complementary permissions, the shape of `decisions/0019` (`Shape0019`); a lapsed precondition owed on `x` that closes one route, where a permission on `x` opens the same route (`ClosingPrecondition`); two `T` permissions whose preconditions are owed on `x` and on `¬x` (`ComplementaryPreconditions`); and the self-contradictory finding (`SelfContradiction`). The instances found for the second and third list nothing at all: a definite `Pending` can list an empty frontier.
- **P, which candidates survive.** The model forms the listed frontier from the ready and pending candidates that no `T` prohibition removes, because `U` atoms eliminate nothing (`due2-workflows.md` §6.2), as clingo-i does (`explain.lp`, `listed`). Removing a candidate in the completions where a `U` prohibition is `T` would be a different rule, and a further shape of omission.
