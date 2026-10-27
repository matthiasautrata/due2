# due2 — Overview

This is the first document to read. It says what due2 is and why, what this repository holds, how an evaluation works, and how to use the repository's semantics program as an oracle beside another ODRL evaluator. Each section ends where a longer document takes over. Where the project stands is in `README.md` § Status, not here.

## What due2 is

due2 evaluates ODRL 2.2 policies. ODRL is the W3C language for saying who may, must, or must not do what with an asset. Given a policy, an access request, and a frozen snapshot of the state of the world (the SOTW), due2 answers with one of five verdicts:

| Verdict | Meaning |
|---|---|
| `Permit` | The request is allowed. |
| `Deny` | A prohibition that applies forbids it. |
| `Pending` | It is allowed once some duties are done. The answer lists every alternative set of duties (the frontier). |
| `NotApplicable` | No rule speaks to it. |
| `Indeterminate` | The data is incomplete, and completing it could change the answer. The answer names the unknowns that matter and the range of verdicts they allow. |

Each verdict comes with the obligations in force and their status (fulfilled, outstanding, violated, or unknown), and with a trace from which a reader can re-derive the verdict.

## Why it is built this way

Three properties shape the design. The first is what sets due2 apart from every external evaluator whose suite the corpus translates (`conformance/external/README.md`); the other two make a decision auditable.

- **Unknown is never false.** Evaluation is three-valued: true, false, or unknown (Kleene logic). A fact that is missing, invalid, in conflict, or unresolved makes the parts that read it unknown, and the unknown survives to the verdict. An evaluator that read a missing purpose as "not compliance" would decide on a reason that is not in the data. due2 says `Indeterminate` and names the missing purpose (`due2-workflows.md` §6.4, `decisions/0011`).
- **The answer explains itself.** The trace records every atom's finding and the reads behind it, and the explanation is the part of the trace the verdict depends on (`decisions/0010`). A verdict whose reasons cannot be reconstructed is not auditable.
- **A decision can be replayed.** The policy, request, and SOTW are values with content digests, and evaluation is a pure function of them, so a recorded decision can be re-run and must give the same trace (`decisions/0007`, `due2-workflows.md` §7).

The example below shows the first property on a real policy.

## How an evaluation works

An evaluation has three workflows (`due2-workflows.md` §1):

| Workflow | Takes | Gives | When |
|---|---|---|---|
| **W1 normalise** | an ODRL policy (Turtle) and its profiles | a *corpus*: the policy flattened into *atoms*, each one rule narrowed to one action, one target, one party per function, and a conjunction of constraints; or a rejection naming what is malformed | once per policy version, offline |
| **W2 evaluate** | the corpus, the request, the SOTW | one three-valued *finding* per atom: does it apply, is it in force, is it fulfilled | per request; each atom on its own |
| **W3 resolve** | the findings | the verdict, the frontier, and the obligations | per request; reads nothing but the findings |

Before W2, a `plan` step reads the corpus and the request and says which facts the SOTW must hold, so the caller fetches only those. The evaluator's interface is two pure functions (`due2-platform.md` §2.1):

```text
plan(corpus, request)         -> reads   (which facts to fetch)
decide(corpus, request, sotw) -> trace   (W2 then W3; the verdict is in the trace)
```

Each argument and result is a JSON document in canonical form, named by its digest (`decisions/0007`). Their relations are fixed in `due2-workflows.md` §3, and `schema/` gives them as JSON Schema. The corpus is the boundary between W1 and the rest: a W2/W3 implementation reads only the corpus, never ODRL (`decisions/0027`).

**Example.** The case `conformance/cases/dprod-audit-logs` holds an offer on an audit-log archive, written with DPROD Contracts, an ODRL profile for data products (`due2-profiles.md` §8). It permits `read` for the purpose `compliance`, prohibits `modify` and `export`, and states an obligation to delete when the retention period exceeds seven years (`P7Y`). The purpose and the retention period are request parameters. A *case* is one or more policies and its *scenarios*; a scenario is one request, one SOTW, and the hand-derived expected answer (`conformance/README.md`). Two of this case's scenarios, as clingo-i answers them:

| Scenario | Verdict | Why |
|---|---|---|
| *read without stating the purpose*: retention `P8Y` | `Indeterminate`, range `NotApplicable` to `Permit` | The permission's purpose constraint is unknown (`odrl:purpose`, status `missing`), and nothing else decides the read. If the purpose is `compliance`, the read is permitted, and otherwise no rule applies. The deletion obligation is in force and outstanding. |
| *retention stated in days against a limit in years*: purpose `compliance`, retention `P730D` | `Permit`, deletion obligation `unknown` | The permission holds. `P730D` is a day-time duration and `P7Y` a year-month one, and `gt` is not defined across the two (`due2-profiles.md` §4), so the obligation's *guard*, the constraint on when it is owed, is unknown (status `misfit`), not false. |

The case's `why` fields give the full derivations. `due2-architecture.md` §0 walks a second request, with a recurring delivery duty, through every stage.

## Design choices

| Choice | Why | Record |
|---|---|---|
| Kleene three-valued logic; `Indeterminate` only when the unknowns can change the verdict | Reports what the data supports, and no more | `due2-workflows.md` §6.4, `decisions/0011` |
| Policies are normalised once into flat atoms | Evaluation per request becomes a map over atoms and a fold over findings, each easy to test | `due2-architecture.md` §3, `odrl-compound-to-atomic-normalization.md` |
| ODRL extensions are declared as data (profiles), and every left operand has exactly one binding: where its value comes from | An evaluator has no hidden vocabulary, and an unbound operand is a rejection, not a silent false | `due2-profiles.md` §2–§3, `decisions/0020`, `0047` |
| A policy error is rejected when the policy is published, never repaired at evaluation | A malformed policy fails loudly once, not quietly per request | `due2-diagnostics.md`, `due2-workflows.md` §4 |
| Inputs and outputs are values named by digest, and evaluation is pure | Replay, caching, and audit need no further machinery | `decisions/0007`, `due2-workflows.md` §7 |
| The trace is the explanation | Explanation cannot drift from evaluation | `decisions/0010` |
| The semantics are written once, as a clingo program, which serves as the oracle | A second derivation of every verdict, independent of the production code | `decisions/0009`, `0027` |
| The corpus of hand-derived cases is the contract between implementations | Any implementation, in any language, is held to the same answers | `conformance/README.md`, `decisions/0027` |

## What this repository holds

| Part | What it is | Where |
|---|---|---|
| Specification | The semantics of W1–W3, the data model, the laws an implementation must satisfy (L1–L10), profiles, and every diagnostic | `docs/spec/` |
| Design | This overview, the architecture and its reasons, the platform around the evaluator, and the bibliography | `docs/design/` |
| Decisions | One record per settled question the specification depends on | `docs/decisions/README.md` |
| Correctness | Which check guards which risk, and the engineering discipline | `docs/correctness/` |
| Conformance corpus | Cases of ODRL policies with scenarios (request and SOTW) and hand-derived expected answers, some translated from other evaluators' suites | `conformance/` |
| Checkers | Admissibility of a policy (`tools/check_corpus.py`), ODRL 2.2 validity (`tools/check_odrl22.py`), the completion algorithm against brute force (`tools/check_completion.py`) | `tools/` |
| Evaluator port schema | `plan` and `decide` inputs and outputs in JSON Schema, generated from `due2-workflows.md` §3 | `schema/` |
| clingo-i | The semantics program: reads an authored ODRL policy, a request, and a SOTW, and answers as due2 would | `spikes/clingo-i/` |
| Formal models | Alloy models of the specification's central claims | `formal/alloy/` |

`README.md` § Status says which of these parts are complete and what comes next.

## Using clingo-i as an oracle

clingo-i answers a scenario from the authored policy: it does W1, W2, and W3 in one call, in a generic clingo program that follows `due2-workflows.md` §5–§6 rule for rule (`spikes/clingo-i/DESIGN.md`). It is the reference for what due2 answers. It is not a production evaluator (`decisions/0027` #4): it is a direct interpreter, built to be read and checked, and it declines what it does not implement rather than guess (`spikes/clingo-i/DESIGN.md` § Declines).

To compare another evaluator with it, translate that evaluator's inputs into due2's, ask clingo-i, and triage every difference.

**0. Run it once.** clingo-i needs `uv` and the Python of `.python-version`; its own dependencies install on first use. `uv run pytest --backend=clingo-i -k dprod-audit-logs` runs the example's scenarios through it and compares them with the expected answers (`spikes/README.md` § Running).

**1. Translate the inputs.**

- *Policies* become ODRL 2.2 Turtle. Every left operand needs a binding: a source (the request, the state of the world, or a built-in) and a property (`due2-profiles.md` §3). An operand that no shipped profile binds is declared in the policy graph itself, as `ex:retentionPeriod` is in the example's `policy.ttl` (`decisions/0020`). Several policies that apply together are passed together, as one corpus.
- *Requests* become the `request` object of `case.json`: `reference`, `action`, `target`, `at`, `parties`, and `params` (`conformance/README.md` § `case.json`). An absent parameter is `missing`.
- *The state of the world* becomes the `sotw` object: `effective_at`, the instant the world is observed; `facts`, each with a status (`resolved` with values, or `missing`, `invalid`, `conflict`, `unresolved`); `evidence` that duties were performed; `activation`, when each duty was first owed; and `closure`, hierarchy edges the policy does not state. A fact the source system lacks is stated `missing`, not given a default value; a state fact left out is read as `unresolved`. These statuses are where the unknowns come from.

**2. Check admissibility first.** `uv run python tools/check_corpus.py <policy.ttl>` checks, without evaluating, that a policy is within the admitted profile and that every operand is bound; `tools/check_odrl22.py` checks ODRL 2.2 validity. A policy that fails names a construct due2 does not accept, which is itself a finding about that policy (`due2-platform.md` §4, *Order*). The corpus's negative cases, the policies W1 must reject, are not run against clingo-i (`spikes/README.md` § `interpret`), so the checkers, not clingo-i, are the gate for admissibility.

**3. Ask clingo-i.** clingo-i speaks a JSON-lines protocol over stdin and stdout (`spikes/README.md` § Protocol): one `init` message carrying the profile modules, then one `interpret` request per scenario, each answered by an output, an `error` (the policy is rejected, or the input is malformed: `spikes/clingo-i/DESIGN.md` § Errors), or `unsupported` (a declined feature, named). The input and output fields are in `spikes/README.md` § `interpret`. The repository's own harness drives it this way, and a caller can reuse it. Run from the repository root with `PYTHONPATH=tools uv run python`, this asks the scenario of the example table's first row:

```python
import json
from pathlib import Path
from harness.backend import Session, load_spike
from harness.corpus import STANDARD_PREFIXES, init_message

case_dir = Path("conformance/cases/dprod-audit-logs")
case = json.loads((case_dir / "case.json").read_text())
scenario = case["scenarios"][2]  # "read without stating the purpose"

session = Session(load_spike(Path("spikes/clingo-i")), init_message())
try:
    reply = session.call(
        "interpret",
        f"{case['case']}/{scenario['name']}",
        {
            "case": case["case"],
            "scenario": scenario["name"],
            "policies": [(case_dir / "policy.ttl").read_text()],
            "prefixes": {**STANDARD_PREFIXES, **case["prefixes"]},  # every prefix the input uses
            "request": scenario["request"],
            "sotw": scenario["sotw"],
        },
    )
finally:
    session.close()
# One of reply.output, reply.error, reply.unsupported is set; reply.ms is the call's wall time.
print(reply.output)  # verdict Indeterminate, verdict_range NotApplicable..Permit, ...
```

Write names in `request` and `sotw` as absolute IRIs, or declare every prefix they use in `prefixes`. A name whose prefix is undeclared would match no policy term, so clingo-i answers it with an `error` that names the field and the prefix (#146).

The backend's stderr goes to `spikes/clingo-i/.stderr.log`. A call takes tens of milliseconds, by the median in `spikes/clingo-i/scorecard.json`, which suits an offline or shadow comparison.

**4. Compare.** Compare what the other evaluator reports: at least the verdict, and the obligations or the frontier if it has them. A field it does not report stays uncompared; it is never filled in. Decide once, and record with the mapping, which of the five verdicts each of its answers agrees with: a deny-by-default evaluator's deny, for example, may stand for `Deny` or for `NotApplicable`, and a two-valued answer has no equal of `Pending` or `Indeterminate`. Expect differences of kind wherever the data is incomplete: an evaluator that reads missing data as false gives `Permit`, `Deny`, or `NotApplicable` where clingo-i gives `Indeterminate`, or reports an obligation that clingo-i reports `unknown`. clingo-i's `unknown_parts` names the input behind each unknown, which groups such differences by cause.

**5. Triage each difference.** Neither side is assumed right. The outcomes extend the three of `due2-platform.md` §4 by the second and the last:

- a defect in the other evaluator;
- a difference of semantics, chiefly the treatment of unknowns, which is explained as a class once and not case by case;
- a gap in due2's specification, which becomes an issue;
- a disagreement worth keeping, which becomes a conformance case under the corpus rules (`conformance/README.md`), stated in generic terms;
- a fault in clingo-i, where it disagrees with a derivation from `due2-workflows.md` §5–§6, which is fixed in clingo-i, with a case that shows it (`correctness-strategy.md` §6).

**What clingo-i declines.** A declined scenario is not compared. The declines are listed in `spikes/clingo-i/DESIGN.md` § Declines. Those a translated policy is most likely to meet are:

- a predicate the program does not read, in the `odrl:`, `due2:`, or a profile's namespace, or on a policy, rule, or duty node, such as `odrl:remedy` or `odrl:inheritFrom` (`unsupported: <predicate>`);
- the occurrences of a recurring duty (`unsupported: recurrence`, #80);
- more than 64 completion variables (`unsupported: variable-cap`).

clingo-i does not emit `frontier_complete` (#103), and has no inexact fallback, so the harness itself declines a scenario that expects one.

**What stays with the other evaluator.** The mapping from its policies, requests, and data into due2's forms, its endpoints, and its data belong with the deployment that runs it, not in this repository (`due2-platform.md` §4).

## Interfaces and their standing

**[D]** marks a decided item and **[O]** an open one, as in the specification.

| Interface | Defined in | Standing |
|---|---|---|
| Corpus, request, SOTW, reads, trace, lineage: the relations | `due2-workflows.md` §3 | [D] |
| Their JSON form, and the `plan` and `decide` inputs and outputs | `schema/`, `decisions/0007` | Generated from the relations |
| W1 rejections and warnings | `due2-diagnostics.md` | [D] codes and shape; no JSON Schema |
| A crash (`Error(cause)`) | `due2-workflows.md` §7 | [D] meaning; no JSON Schema |
| The case format | `conformance/README.md` | Checked by `tools/check_corpus.py` |
| The spike protocol: `interpret` | `spikes/README.md` | Implemented by clingo-i |
| The spike protocol: `decide`, on relation-level vectors | `spikes/README.md`, `conformance/README.md` | Specified; vectors are #37 |
| The platform's other components (ledger, policy store, SOTW services, catalog) | `due2-platform.md` §2 | [O] sketches |

## Where to read next

- `due2-architecture.md`: the normal form, what normalisation does, verdicts and combination, the glossary (§0), and the prior work due2 builds on (§8).
- `due2-workflows.md`: the normative semantics. §5 and §6 decide every verdict.
- `due2-profiles.md`: how operands are bound and compared, and DPROD Contracts compatibility.
- `due2-platform.md`: the components around the evaluator, and §4, the migration from a predecessor.
- `conformance/README.md`: the case format, and the coverage gaps.
- `spikes/README.md` and `spikes/clingo-i/DESIGN.md`: the protocol, and how the semantics program works.
- `correctness-strategy.md`: which check guards which risk, and what each oracle is independent of.
