# Alloy models

Each claim of `correctness-strategy.md` §4.8 gets a small Alloy 6 model, which searches for a counterexample within a bound on the size of each signature (`decisions/0021`). A `check` that finds none shows the claim only up to that scope. A `run` shows that an instance exists, either a known gap or a witness that a check is not vacuous. A counterexample is triaged by `correctness-strategy.md` §6.

The models are not part of README § Verify. They belong to the slow tier (`correctness-strategy.md` §7), whose results feed the ratchet, not the gate, and `.github/workflows/slow.yml` runs them nightly. Run them with

```bash
formal/alloy/run.sh                          # every model
formal/alloy/run.sh formal/alloy/<model>.als # one model
```

The script needs Java 17 or later, curl, and python3. It runs Alloy 6.2.0, the Maven artifact `org.alloytools:org.alloytools.alloy.dist`, and checks the jar against the SHA-256 digest pinned in `run.sh`. It uses the jar in the local Maven repository (`~/.m2`) if there is one there. Otherwise it downloads the jar once into `~/.cache/due2/`, from Maven Central or from the repository named by `DUE2_MAVEN_REPO`, such as a mirror of Maven Central. Credentials for the download go in `~/.netrc`. Where only Maven can reach the mirror, run `mvn dependency:get -Dartifact=org.alloytools:org.alloytools.alloy.dist:6.2.0` first. Each command prints one line with its outcome: `UNSAT` when a `check` finds no counterexample or a `run` no instance, and `SAT` when it finds one. Each command states the outcome it expects with Alloy's `expect` (`expect 0`: none; `expect 1`: one exists), as the table below lists, and `run.sh` exits 1 when a command states none or its outcome differs. A model with no commands, `resolve.als`, is compiled by the models that open it.

## Models

| Model | Claim | Spec sections |
|---|---|---|
| `k_completion_key.als` | K: the completion key is sound, and one-sided at the leaves | `due2-workflows.md` §5.4, §6.4; `due2-profiles.md` §3, §4; `decisions/0012`, `0015`, `0016`, `0023` |
| `kleene_regularity.als` | The connectives are regular, which carries K's one-sidedness from the leaves to the findings | `due2-workflows.md` §5.2; `decisions/0016` |
| `resolve.als` | None: a module, W3 over one completion, opened by the four models below | `due2-workflows.md` §6.1–§6.4 |
| `m_monotonicity.als` | M: the verdict is monotone in every finding, and the uniform variables are bounded by the two extremes | `due2-workflows.md` §6.4 |
| `f_frontier_relevance.als` | F: two `Pending` completions that agree on the relevant unknowns have one frontier, and the same open routes | `due2-workflows.md` §6.4; `decisions/0004`, `0026` |
| `w_basis_waiver.als` | W: a definite `Permit` or `Deny` with an empty basis has a `U` finding on a variable that another literal reads too | `due2-workflows.md` §6.4; `decisions/0016` |
| `p_listed_frontier.als` | P: the listed frontier, the non-dominated routes that suffice, omits no route that every completion offers, and its fallback lists only routes that suffice | `due2-workflows.md` §6.3, §6.4; `decisions/0019`, `0026` |

`resolve.als` leaves out instances, timing, the non-default combinations, and grounds; its header gives the reason for each. A `World` is one completion: every finding in it is `T` or `F`. A model that quantifies over every completion asserts `everyCompletion`: the worlds are closed under flipping one variable, and no two are one completion. Its scope on `World` therefore bounds the unknowns, variables and unknown `fulfilled` findings together: 8 worlds hold every completion of three. At scope 3 there are at most three variables, so a fourth unknown is an unknown `fulfilled` finding.

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
| | `check OpenRoutes` | 6 | no counterexample | none | 1 s |
| `w_basis_waiver.als` | `check Waiver` | 3, 8 worlds | no counterexample | none | 109 s |
| | `run EmptyPermit` | 3, 4 worlds | an instance | found | 1 s |
| | `run EmptyDeny` | 3, 4 worlds | an instance | found | under 1 s |
| `p_listed_frontier.als` | `check NoOmission` | 3, 8 worlds | no counterexample | none | under 1 s |
| | `check PermitListsEmpty` | 3, 8 worlds | no counterexample | none | 2 s |
| | `check FallbackSound` | 3, 8 worlds | no counterexample | none | under 1 s |
| | `run NoSingleGiver` | 3, 4 worlds | an instance | found | under 1 s |
| | `run OpenInSome` | 3, 4 worlds | an instance | found | under 1 s |
| | `run DominatedInSome` | 3, 4 worlds | an instance | found | under 1 s |
| | `run EmptyListed` | 3, 4 worlds | an instance | found | under 1 s |
| | `run InvalidNeedsExclusion` | 3, 4 worlds | an instance | found | under 1 s |

One-sidedness checked in one model, leaves and connectives together, did not finish in five minutes even at scope 3, so it is split into `OneSidedAtLeaves` and `Regular`.

The checks that quantify over every completion grow fast with the worlds. `everyCompletion`'s rule that no two worlds are one completion spares the solver their permutations: before it, `check Waiver` at 8 worlds did not finish in ten minutes. The native solver glucose is often faster than SAT4J (`DUE2_ALLOY_SOLVER=glucose`): `check Waiver` takes 50 s with it, and at 16 worlds, every completion of four, it finds no counterexample in 13 minutes.

## Findings

Each counterexample is triaged by `correctness-strategy.md` §6.

- **W, an overflow.** A `check Waiver` that counts the literals reading a variable with Alloy's integers finds a false counterexample: their default width of 4 bits wraps a count of 8 to −8. The error is the model's, so `readTwice` states "read twice" without arithmetic, and the check finds no counterexample.
- **P, the fallback's exclusion.** Beyond `max_frontier_vars`, W3 lists the routes of the candidates that are ready or pending whatever the unknowns are, and that no completion removes in `due2-workflows.md` §6.2 (§6.4, *Computing it*). Read as "no `T` prohibition removes", that is unsound: under `invalid`, a `U` prohibition voids the policy in the completions where it is `T`, so its candidate does not survive there (`InvalidNeedsExclusion`). The fallback therefore leaves out a candidate whose policy is under `invalid` with a `U` prohibition, and `FallbackSound` then finds no counterexample.
- **P, the question.** The shapes the model found while P was open are recorded in `decisions/0026` § Question.
