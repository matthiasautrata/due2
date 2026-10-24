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

## Scopes and times

Measured on 2026-10-23 with Alloy 6.2.0, its default SAT4J solver, and Java 27 on an arm64 Mac, one command at a time. The scope bounds every signature.

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

One-sidedness checked in one model, leaves and connectives together, did not finish in five minutes even at scope 3, so it is split into `OneSidedAtLeaves` and `Regular`.
