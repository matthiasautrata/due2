# due2 conformance corpus

Cases are input/expected-output pairs in the reference data model of `due2-workflows.md`. They are written to be run by an evaluator; `tools/check_corpus.py` checks everything that can be checked without one.

```bash
uv run python tools/check_corpus.py conformance/cases          # every case
uv run python tools/check_corpus.py conformance/cases/<case>   # one case
uv run python tools/check_corpus.py profiles/vendor/dprod/examples/*.ttl   # the vendored DPROD examples, as policies
```

## Layout

```text
conformance/cases/<case>/
    policy.ttl     one ODRL policy, plus the operand bindings it uses
    case.json      provenance, classification, and scenarios — or, for a negative case, the expected rejection
conformance/vectors/<file>.json
                   a relation-level vector file: a corpus written as relations, and scenarios against it
```

Case names start with their origin: `rl2-` for the RL2 use cases (`github.com/matthiasautrata/RL2`, `conformance/usecases/`), `dprod-` for DPROD Contracts examples (`github.com/EKGF/dprod`, `develop`, `dprod-contracts/examples/`), `force-`, `oval-`, and `w3c-fs-` for other evaluators' suites (vendored under `external/`, see `external/README.md`), and `due2-` for cases authored here to cover what no origin exercises.

## Running a backend

Each positive scenario is a vector of the `interpret` task: its policy, request, SOTW, and config in, its `expected` out. `uv run pytest --backend=<spike>` runs every vector against a spike under `spikes/`; the protocol, output shape, and comparison rules are in `spikes/README.md`. Negative cases are not `interpret` vectors; they wait for W1, the normaliser. Each scenario of a relation-level vector file is a vector of the `decide` task (see Relation-level vectors, below).

## Vendored DPROD examples

The upstream example policies themselves are vendored unmodified under `profiles/vendor/dprod/examples/` — four files, sixteen policies: eleven offers and contracts in `baseline.ttl`, two in `data-contract.ttl`, two in `data-use-policy.ttl`, one in `odcs.ttl` — so the DPROD-compatibility claims are reproducible locally: the command above checks all sixteen against due2's admitted input profile, the DPROD profile selected by their own `odrl:profile`. `tools/check_corpus.py` expects twelve of them to be rejected, all from `baseline.ttl` and `odcs.ttl`: those files define the action `ex:conformTo` without the `odrl:includedIn` that ODRL IM §2.4 requires, so W1 rejects every policy in them with `InvalidActionHierarchy` (`decisions/0034`, reported upstream as EKGF/dprod#286). The checker fails if one of the two files passes. The `dprod-*` cases that extract their policies state the edge.

The `dprod-*` cases cover every one of the sixteen vendored policies with scenarios and hand-derived verdicts, plus constructed cases (`dprod-divergences`, `dprod-not-negated-purpose`) that demonstrate the six documented divergences. Cases extract their policy from the vendored file, naming anonymous rules and dropping DPROD's input `dprod:dutyState` triples (due2 derives status from evidence and activation instead); the `source` field names the file and policy, and `notes` records every such change.

## `policy.ttl`

- Exactly one policy, typed `odrl:Set`, `odrl:Offer`, `odrl:Agreement`, or a profile subclass such as `dprod:DataContract`.
- ODRL 2.2 vocabulary for everything ODRL has. Profile terms only from the extension points of `due2-profiles.md` §2, and the policy names its profiles with `odrl:profile`. Every action, left operand, operator, function, relation, and conflict value is an `odrl:` term, a term of a declared profile, or a term the policy types itself, such as `ex:display a odrl:Action` (`decisions/0020`). A `cc:` action needs a profile.
- Every rule is named (an IRI), so expected results can refer to it.
- Every left operand used is bound with `dprod:operandSource` and `dprod:operandProperty` (`due2-profiles.md` §3), either in the file or in a selected profile. Give `rdfs:range` wherever the type matters.
- Duty timing on duty rules only: `dprod:deadline` — an `xsd:dateTime`, or a single-kind `xsd:duration` relative to activation — and `dprod:recurrence`, an RRULE string containing `FREQ=` (`due2-profiles.md` §7).
- An explicit `odrl:conflict` unless the case is about the default.
- Self-contained: actions, parties, assets, and hierarchy edges the case needs are in the file — except what the shipped profile modules in `profiles/` already supply, such as ODRL's action hierarchy (`odrl:read ⊑ odrl:use`).
- Domain actions, assets, parties, and operands (`ex:retrieve`, `ex:requestedRecords`) are domain vocabulary. They do not count as profile terms for classification.

## `case.json`

```json
{
  "case": "rl2-volume-limit",
  "source": "RL2 conformance/usecases/volume-limit.md",
  "classification": "odrl-core",
  "needs": [],
  "notes": "How the RL2 original maps, and anything lost or changed.",
  "prefixes": { "ex": "https://example.org/" },
  "scenarios": [
    {
      "name": "the subscriber retrieves",
      "request": {
        "reference": "req-1",
        "action": "ex:retrieve",
        "target": "ex:DataService",
        "at": "2026-06-01T00:00:00Z",
        "parties": { "odrl:assignee": "ex:Subscriber" },
        "params": { "ex:requestedRecords": { "@value": "12000", "@type": "xsd:integer" } }
      },
      "sotw": {
        "effective_at": "2026-06-01T00:00:00Z",
        "facts": {
          "ex:requestedWithinRemaining": { "status": "resolved", "values": [ { "@value": "true", "@type": "xsd:boolean" } ] }
        },
        "evidence": [],
        "activation": {},
        "closure": []
      },
      "config": { "combination": "prohibit-overrides" },
      "expected": {
        "verdict": "Permit",
        "frontier": [],
        "obligations": [],
        "why": "The one permission's action, target, and assignee match the request, and it has no constraints or duties, so it is ready."
      },
      "rl2_expected": "Permit"
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `classification` | `odrl-core` — ODRL 2.2 plus operand bindings. `odrl-profile` — needs a profile term from `due2-profiles.md` §2. `partial` — some scenarios or aspects cannot be expressed. `not-expressible` — needs semantics outside due2's extension points; the closest ODRL is still written. |
| `needs` | For anything but `odrl-core`: the profile terms used, or the constructs missing. |
| `request.params` | Values of `dprod:requestSource` properties, keyed by property IRI. Absent means `missing`. An operand with `due2:cardinality due2:set` takes a JSON list of values (`oval-list-right-operand`). |
| `sotw.facts` | Values of `dprod:stateSource` properties: `status` is `resolved`, `missing`, `invalid`, `conflict`, or `unresolved`; `values` has one entry when resolved (any number, including none, for an operand declared `due2:cardinality due2:set`), two or more when in conflict, none otherwise. |
| `sotw.evidence` | `id`, `occurred_at`, `actor`, `action`, optional `object`, `issuer`, `discharges`, `params` (`due2-workflows.md` §3.3). `params` are read by `due2:witnessSource` operands in a duty's constraints (`due2-profiles.md` §3). `discharges` names the grant the evidence was submitted against by the inputs of its digest, `{"duty": IRI, "reference": <request reference>}`; the evaluator computes the digest (`due2-workflows.md` §5.3). |
| `sotw.activation` | Duty instance key or rule IRI → activation instant, an `xsd:dateTime`, for relative deadlines and recurrence anchors (`due2-workflows.md` §5.3, `due2-profiles.md` §7). |
| `sotw.closure` | `[relation, narrower, broader]` triples, for hierarchy edges not in the policy file. |
| `config` | `combination`; optional `preference`, `signers` (a list of `{"duty": IRI, "issuer": IRI}`, `due2-workflows.md` §3.4), `violations` (`ignore` by default, `deny` for DPROD-aligned evaluation — exception 6 of `due2-profiles.md` §8.2 still diverges), `admit_source`, `admit_age`. |
| `expected.verdict` | `Permit`, `Deny`, `Pending`, `NotApplicable`, or `Indeterminate`, derived by hand from `due2-workflows.md` §5–§6 and `due2-profiles.md`. |
| `expected.frontier` | For `Pending`: a list of alternatives, each a list of outstanding duty IRIs. |
| `expected.exact` | Optional, and only meaningful when unknowns could affect the verdict: `false` asserts that it comes from the beyond-`max_mixed` fallback (`due2-workflows.md` §6.4), `true` that the completion was exact (`due2-max-mixed`). |
| `expected.obligations` | Obligations in force for the request (`due2-workflows.md` §5.2, §6.1): `{"duty": IRI, "status": "fulfilled" \| "outstanding" \| "violated" \| "unknown"}`, plus `"instance": <occurrence instant>` for an instance of a recurring duty. Statuses follow the table of `due2-workflows.md` §5.3 — W2 computes them from the witness finding and the deadline; include `unknown` ones too, and remember that a recurring obligation with no instance owed yet is not reported. |
| `expected.verdict_basis` | Optional: the atoms that determined the verdict, by role, at the authored level (`due2-workflows.md` §3.7, §6.4) — a set of `{"ref": IRI, "role": R}`. `ref` is the rule IRI, or the duty IRI for roles `duty` and `obligation`; the disjuncts of one rule are one entry. Roles: `prohibition` (the surviving `T` prohibitions of a `Deny`), `permission` (a `Permit`'s ready permissions, a `Pending`'s frontier permissions), `duty` (a `Pending`'s outstanding duties — exactly the frontier's when no unknown part is listed), `unknown` (an `Indeterminate`'s `U` atoms with a pivotal literal, `decisions/0011`), `closed` (a `NotApplicable`'s candidates removed by a violated precondition), and `obligation` (every obligation in force under any verdict — exactly `expected.obligations`' duties). Under unknowns each role names the atoms that play it in every completion, so a verdict that holds by cases, such as a `Deny` from two prohibitions on `x eq 5` and `x neq 5` with `x` unresolved, can have no `prohibition` (`due2-workflows.md` §6.4, `decisions/0016`). A `Pending` that lists an unknown part of any status may lack `permission` or `duty`, and its duties may differ from the frontier's, because its frontier varies by dominance (`decisions/0019`). Absent means not asserted; `[]` asserts that nothing determined it. |
| `expected.eliminated` | Optional: the atoms removed, the atom that removed each, and the rule — a set of `{"ref": IRI, "by": IRI, "rule": X}` (`due2-workflows.md` §3.5, §6.1–§6.2). `X` is the policy's `conflict` (`prohibit`: a permission by a `T` prohibition; `perm`: a prohibition by a `T` permission; `invalid`: every permission and prohibition of the void policy, by each `T` permission and prohibition other than itself; its root obligations stay, `decisions/0029`), `violated_precondition` (a permission by its violated duty; with `verdict_basis`, the `closed` entries of a `NotApplicable` are exactly these), or the cross-policy `combination`. Absent means not asserted. |
| `expected.verdict_range` | Optional, for an `Indeterminate` only: the least and the greatest completion verdict, `{"low": V, "high": V}`, in the order `Deny < NotApplicable < Pending < Permit` (`due2-workflows.md` §3.5, §6.4, `decisions/0011`). `low` is below `high`, and neither is `Indeterminate`. Absent means not asserted. |
| `expected.unknown_parts` | Optional: every `U` part of every rule's atoms whose finding is `T` or `U`, and of every duty's findings that are `T` or `U` (a guard, a witness condition, or `odrl:assignee`, the bearer's party function, when the request names no subject), whether or not it determined anything, under any verdict (`due2-workflows.md` §3.5, §3.7, `decisions/0016` and its amendment). It projects the trace's `unknown_part` and `witness_part` together: a witness condition read against two witnesses with two statuses is two entries (`decisions/0035`) — a set of `{"ref": IRI, "input": IRI, "status": S}`. `ref` is the rule or duty IRI, and the parts of one rule or duty that read one input with one status are one entry. `input` is what the part reads: `odrl:target`, a party function such as `odrl:assignee`, or the operand's property. `status` is `missing` (no value: an absent target, party, or parameter, a state fact `missing`, or `resolved` with no value for a single-valued operand), `invalid`, `conflict`, `unresolved` (a state fact `unresolved`, or none), or `misfit` (a resolved value that does not fit the operator, `due2-workflows.md` §5.4). Absent means not asserted; `[]` asserts that every part was known. |
| `expected.why` | The derivation in one or two sentences — which atoms applied, which were unknown, why the verdict follows. |
| `rl2_expected`, `dprod_expected`, `force_expected`, `oval_expected`, `w3c_expected` | The origin's own expected result, where it states one, in the origin's vocabulary (FORCE: rule kind and activation state; OVAL: accept decision under its semantics switches; W3C CG: activation and control state). A difference from `expected.verdict` is explained in `notes`. |

**Negative cases.** A case whose policy W1 must reject carries `expected_rejection` instead of `scenarios`:

```json
"expected_rejection": {
  "codes": ["MissingTarget"],
  "why": "The permission has no odrl:target, at rule or policy level; `odrl-compound-to-atomic-normalization.md` §6.3 rejects it in stage 1."
}
```

- `codes` is the exact set of error codes W1 returns, from `docs/spec/due2-diagnostics.md` §3. W1 reports every error of the first failing stage and runs no later stage (`due2-diagnostics.md` §1), so the set is deterministic. `tools/check_corpus.py` compares it with what it emits.
- `why` names the defining section, as a scenario's `why` does.
- `odrl22_valid: false` marks a policy that is not valid ODRL 2.2, for example FORCE policies 1–7, which have no target. `tools/check_odrl22.py` then expects the shape to fail it (`xfail`) and fails if it conforms. Omitted, it means `true`: the rejection is due2's own (`due2-witness-outside-duty`). Only a negative case may set it to `false`.
- The origin's results are kept as they are on a translated scenario. `force-01` … `force-07` keep FORCE's test cases as a `force_expected` list of `{test_case, title, request, sotw, result}`; `oval-untyped-datetime` keeps OVAL's as an `oval_expected` list of `{test_case, title, request, result}`. A case translated from one of OVAL's validation files names the file as `test_case` and OVAL's expected rejection as `result`, with `title` and `request` null, because a validation file has neither.

**Values.** A literal is `{"@value": ..., "@type": ...}`, an IRI `{"@id": ...}` — the JSON-LD forms. Prefixed names expand through `prefixes`.

**Classification.** Context built-ins (`dprod:clock`, `dprod:agent`, `due2:actionTime`), `due2:witnessSource`, and the binding properties themselves are operand-binding vocabulary, not profile terms: a case that uses only them still classifies as `odrl-core`. Profile terms are the extension points of `due2-profiles.md` §2 — `dprod:not`, `dprod:deadline`, `dprod:recurrence`, `dprod:subjectOfDuty`, policy subclasses.

**Profile declaration is separate from classification.** IM §2.1 requires a policy that uses non-Core vocabulary to declare the profiles whose terms it uses — and the binding properties (`dprod:operandSource`, `dprod:operandProperty`) are DPROD-vocabulary terms appearing in the policy. So a case can classify `odrl-core` and still carry `odrl:profile <https://ekgf.org/dprod/spec/develop/>` (and `<https://w3id.org/due2/profile#>` when it uses `due2:` terms). `tools/check_corpus.py` rejects an undeclared namespace as a W1 input error — normalisation selects a profile's binding module by `odrl:profile` — and `tools/check_odrl22.py` checks the same rule against the IM directly. Both also reject a term from any other namespace that neither a declared profile nor the policy defines (`UndeclaredProfile`, `decisions/0020`).

**Standing divergences from RL2,** which a case need not re-explain:

- An unfulfilled precondition gives due2 `Pending` with the route, where RL2 gives `NotApplicable`.
- due2 closes `odrl:partOf` transitively; RL2 core matches only direct members.
- due2 evidence is existential: any witness fulfils a duty, so RL2's conflicting-evidence scenarios have no counterpart.
- Completion is over literals, so two permissions on complementary values of one `unresolved` fact give a definite verdict, where RL2, which treats every occurrence of a shared fact as independent, gives `Indeterminate`. A `missing`, `invalid`, or conflicting value still gives `Indeterminate` (`due2-workflows.md` §6.4, `decisions/0016`, `due2-unresolved-or-missing`).

**Standing divergences from DPROD,** which a `dprod-*` case need not re-explain: the six exceptions of `due2-profiles.md` §8.2 — Kleene masking and errors in rules that do not apply, incomparable operands, duty state derived from evidence, Agreement parties, policy-level targets, and violated duties — together with DPROD's duty-collection rule (`formal-semantics.md` §7.2 step 1: a duty is collected only when its own action matches the request), which is why no DPROD duty is ever collected for a read.

Expected results are hand-derived. The derivation in `why` is what a reviewer checks.

## Relation-level vectors

A relation-level vector file gives the W2/W3 evaluator its inputs written directly as relations, together with the traces it must return (`decisions/0006` #3 and #4, kept by `decisions/0027` #5). No policy is normalised, so the evaluator is tested apart from W1, and a W1 defect cannot pass for an evaluator defect. The relations are those of `due2-workflows.md` §3.1–§3.5. Each collection is encoded as `due2-workflows.md` §2 states: a JSON object keyed by relation name, whose values are arrays of tuples.

```text
conformance/vectors/<file>.json    one corpus, and the scenarios evaluated against it
```

A vector file is named like a case, starting with its origin. The directory holds no file until #37; `tests/fixtures/vectors/due2-one-permission.json`, which `tests/test_schema.py` checks, is a complete small one. Each of its scenarios is one vector of the `decide` task (`spikes/README.md`): a request, SOTW, and config, evaluated against the file's corpus, and the expected trace. In this sketch the `…` stand for tuples:

```json
{
  "file": "due2-one-permission",
  "notes": "Anything a reviewer needs beyond each scenario's why.",
  "tags": ["duties"],
  "prefixes": { "ex": "https://example.org/", "odrl": "http://www.w3.org/ns/odrl/2/", "xsd": "http://www.w3.org/2001/XMLSchema#" },
  "corpus": { "policy": [ … ], "atom": [ … ], "atom_party": [ … ], "root": [ … ] },
  "scenarios": [
    {
      "name": "within ceiling and quota",
      "tags": ["temporal"],
      "request": {
        "request": [ { "action": "ex:retrieve", "target": "ex:DataService", "at": { "v": "2026-06-01T00:00:00Z", "t": "xsd:dateTime" } } ],
        "request_party": [ { "function": "odrl:assignee", "party": "ex:Subscriber" } ]
      },
      "sotw": { "sotw": [ { "effective_at": { "v": "2026-06-01T00:00:00Z", "t": "xsd:dateTime" } } ] },
      "config": { "config": [ { "combination": "prohibit-overrides", "violations": "ignore", "max_mixed": 8, "max_frontier_vars": 8 } ] },
      "expected": {
        "trace": { "verdict": [ { "value": "Permit", "frontier_complete": true, "exact": true } ], "eliminated": [] },
        "why": "Both constraints hold; the permission applies and has no duties."
      }
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `file` | The file name without `.json`. |
| `source`, `notes` | Optional. `source` names what the vector file was derived from, such as a case and scenario. `notes` records what changed in the derivation, and anything else a reviewer needs. |
| `prefixes` | Prefix to namespace IRI, for the authoring form below. |
| `tags`, `scenarios[].tags` | Optional. Short labels for what a vector exercises (`duties`, `temporal`); a scenario carries the file's tags and its own. They serve the scorecard's per-tag counts (`spikes/README.md`), which count a scenario once under each of its tags. Tags are test metadata: no collection carries them, and the evaluator never sees them. |
| `corpus` | The corpus (`due2-workflows.md` §3.1). It satisfies the invariants that `due2-workflows.md` §3.1 lists, because W1 establishes them and the evaluator trusts them. Ids the corpus mints, such as `atom_id` and `constraint_id`, are IRIs the author chooses (`ex:a1`). |
| `scenarios[].request`, `sotw`, `config` | The scenario's request, SOTW, and config (`due2-workflows.md` §3.2–§3.4). |
| `expected.trace` | The trace relations the scenario asserts (`due2-workflows.md` §3.5). `verdict` is required, and every other relation is optional. A stated relation is compared with the evaluator's as a set of tuples, exactly, every field included: `[]` asserts that it has no tuples, and an absent relation asserts nothing. So `verdict.exact` is always compared, unlike `expected.exact` of a case. `evaluation` is never stated (below). |
| `expected.why` | The derivation in one or two sentences, from `due2-workflows.md` §5–§6, as in a case. |

**Authoring form.** A vector file is written by hand, so it may differ from the canonical form of `due2-workflows.md` §2 in five ways. The harness canonicalises every collection, the expected trace included, before it sends or compares it.

- A string value may be a prefixed name: when the text before its first colon is a key of `prefixes`, that text and the colon are replaced by the namespace IRI. A full IRI's scheme (`https`, `urn`) is not a key, so it stays as written, and so does a literal's lexical form `v`, which never expands. `party` and `sha256` are not allowed as prefix names, because `constraint.scope` values and digests start with them.
- Tuples may be in any order. The harness sorts them.
- A relation with no tuples may be written as `[]`. The harness omits it.
- A relation may be written as a table, `{"fields": ["atom_id", "function", "party"], "rows": [["ex:a1", "odrl:assignee", "ex:Subscriber"]]}`: each row gives one value per field, in order, and `null` for an optional field the tuple omits. The harness expands each row into a tuple. A row whose length differs from `fields`, or with `null` in a field that is not optional, makes the file invalid. A `null` means only that the field is absent, never that a value is unknown: a property whose value is missing or unresolved is a `fact` whose `status` says so (`due2-workflows.md` §3.3).
- In the expected trace, a `Digest` field may hold a placeholder name, such as `alt1`, instead of a digest (see Derived ids, below). The harness replaces the name with the digest of its UTF-8 bytes, so the trace passes the schema, and every tuple that uses one name gets one value.

Literals take the form `{"v", "t", "l"}` of `due2-workflows.md` §2, not the JSON-LD forms of `case.json`. Set semantics apply to a relation's key (`due2-workflows.md` §2), so a tuple written twice counts once, and two tuples with one key that differ elsewhere make the file invalid. So do a relation or a field that `due2-workflows.md` §3 does not define, a relation with an empty key, such as `verdict`, holding other than one tuple, and an `xsd:dateTime` that names no instant, such as `2026-02-30T12:00:00Z`, whose shape the schema accepts. `check_vector_file` in `tools/harness/vectors.py` checks each file against `schema/` (`schema/README.md`) and against the corpus invariants of `due2-workflows.md` §3.1, and `tests/test_schema.py` runs it on every file under `conformance/vectors/`.

**Ids the vector file does not state.**

- **`evaluation`.** The harness computes the four collection ids from the canonical collections it sends. It compares them with the evaluator's `evaluation` tuple whenever the evaluator declares that relation (`spikes/README.md`, `decide`). A vector file does not state them, because any edit to an input changes them.
- **Derived ids.** An instance key is the duty atom's id, or a UUID built from it with the request's performer, reference, and occurrence (`due2-workflows.md` §5.3), so a vector states it exactly. `alt_id` and `discharges` are digests whose byte construction is open (#107). Until #107 settles it, an expected trace names an `alt_id` by any string of its choosing, and the comparison passes when one one-to-one renaming of those names to the evaluator's, applied across every stated relation, makes each relation equal. The harness searches for the renaming. An input that has to name a grant in `evidence.discharges` cannot be written until #107 is settled.
- **Operand bindings.** The corpus carries no operand bindings, which W2 needs to evaluate a constraint (`due2-workflows.md` §5.4, step 1). Until #108 settles their relations, a vector file cannot state a constraint.

## Coverage gaps

Specified and marked decided, but with no exercising case. Each gap is an authoring task, not a spec change; the list is re-derived by grepping the corpus. **Tracked as GitHub issues** (label `corpus`); this section remains the specification record.

Re-derived 2026-10-24, after `due2-literal-party`, `due2-and-or`, `due2-two-right-operand-references`, `due2-action-without-parent`, `due2-action-two-parents`, and `due2-has-policy` (#117); earlier re-derivations are listed in `docs/archive/changes.md` § `conformance/README.md` § Coverage gaps.

Closed gaps, with the cases that close them:

- **`due2:witnessSource` and `evidence_param`** — `oval-duty-payment`, `w3c-fs-c1`, `w3c-fs-c2` (as duty-action refinements, `due2-profiles.md` §9 #6).
- **Grant scope and `discharges`**, **`signers`** — `due2-grant-signers`.
- **A grant-scoped duty with several targets** — `due2-grant-two-targets` (one instance per atom for the request, so a payment of one fee leaves the other outstanding; `decisions/0032`).
- **`odrl:or`** — `force-20` (260 disjuncts, all known) and `due2-or-unknown` (Kleene, with unknowns).
- **`max_mixed` fallback (`due2-workflows.md` §6.4, beyond the bound)** — `due2-max-mixed` (nine facts each read both ways by an authored permission pair, `expected.exact = false`; scenario 2 sits at the bound, where only exact enumeration decides).
- **`perm` and `invalid` conflict strategies** — `oval-conflict-perm`, `oval-conflict-invalid`.
- **A void policy's root obligations** — `due2-void-keeps-obligation` (under `invalid` and `violations = deny`, a violated obligation of a void policy still denies; `decisions/0029`).
- **Which instant a re-evaluation answers for** — `due2-reevaluation-moves-at` (a re-evaluation's request has `at` moved to its `effective_at`, so a payment made after a window has closed does not reopen it, and one made in time still counts; `decisions/0030`).
- **An unknown fulfilment and a deadline** — `due2-unknown-fulfilment-deadline` (the same unknown payment before and after its deadline: `Pending`..`Permit`, then `NotApplicable`..`Permit`, which W3 tells apart by the instance's `passed`; `decisions/0032`).
- **Incomparable frontier** — `due2-incomparable-frontier` (collapse, dominance, second approver); a declared preference waits on its config field's form (`due2-workflows.md` §9 #3).
- **Requests without a target** — `oval-no-target-permission`, `oval-no-target-prohibition` (`due2-workflows.md` §3.2, §5.2).
- **Canonical literals deciding a verdict** — `due2-xone-unknown` (an `xone` operand read both ways; `due2-workflows.md` §6.4).
- **Unknown duty guards; many conditional duties on one permission** — `due2-conditional-duties` (nine guarded duties, linear and exact, `decisions/0003`) and `w3c-fs-c2` scenarios 4–5.
- **A disjunctive duty condition** — `due2-duty-disjunction` (guards and witness conditions each a disjunction, kept as clauses on the one duty atom; `decisions/0028`).
- **`isPartOf` with a list right operand** — `oval-list-right-operand` (`decisions/0005`).
- **A refined action in each node form** — a blank node (`due2-conditional-duties`), an authored IRI (`w3c-fs-c1`, `w3c-fs-c2`), and a skolem IRI typed `odrl:Action` (`due2-refined-action-skolem`): the action is the node's `rdf:value` in each (`decisions/0034`, amendment of 2026-10-25).
- **`verdict_basis` and `eliminated`** — `expected.verdict_basis` and `expected.eliminated` in the case format (#57), asserted by 80 scenarios: `due2-concept-complement`, `due2-concept-purpose`, `due2-concept-purpose-prohibition`, `due2-duty-disjunction`, `due2-nested-unknowns`, `due2-or-unknown`, `due2-rebound-pay-amount`, `due2-reevaluation-moves-at`, `due2-refined-action-skolem`, `due2-repeated-right-operand`, `due2-shared-reads`, `due2-unresolved-or-missing`, `due2-void-keeps-obligation`, `oval-conflict-invalid`, `oval-conflict-perm`, `oval-conflict-prohibit`, `rl2-pay-to-play`, `rl2-attestation-gating`, `rl2-geo-restriction`. Every verdict and role is asserted, and the eliminations `prohibit`, `perm`, `invalid`, and `violated_precondition`. `expected.verdict_range` (#59) is asserted by the two `Indeterminate` scenarios of each of `due2-or-unknown`, `due2-repeated-right-operand`, `due2-shared-reads`, `due2-concept-purpose-prohibition`, and `rl2-geo-restriction`, the four of each of `due2-unresolved-or-missing` and `due2-nested-unknowns`, the three of `due2-concept-purpose`, and the one of each of `due2-rebound-pay-amount` and `due2-concept-complement`.
- **Atoms that read one absent request field** — `due2-shared-reads` (one target, one assignee, under `invalid`): each atom is completed alone, so `Indeterminate` (`due2-workflows.md` §6.4, `decisions/0016`).
- **Unresolved against missing, misfit, and conflicting values** — `due2-unresolved-or-missing` (`decisions/0016`'s example: a pair of complementary permissions is a definite `Permit` with an empty basis only when the value is unresolved).
- **`unknown_parts`** — `expected.unknown_parts` in the case format (#72), asserted by the 52 scenarios of `due2-shared-reads`, `due2-unresolved-or-missing`, `due2-nested-unknowns`, `due2-duty-disjunction`, `due2-void-keeps-obligation`, `due2-reevaluation-moves-at`, `due2-unknown-fulfilment-deadline`, `due2-refined-action-skolem`, the three concept-scheme cases, `rl2-geo-restriction`, and `dprod-audit-logs`, whose obligation is `unknown` on a missing retention period. Every status is asserted, `invalid` by a concept in no declared scheme, and the inputs `odrl:target`, `odrl:assignee`, a state property, `odrl:purpose`, and a witness's evidence parameter (`due2-duty-disjunction`, an amount missing from the witness).
- **Unknown parts in nested trees** — `due2-nested-unknowns` (an `xone` with a decided member, an `or` of an `and`, an `and` of an `or`, and an `or` over a negated `or`): a `U` leaf that lies only in `F` atoms is not named, and one that decides nothing is (`due2-workflows.md` §3.5, `decisions/0016`, amendment).
- **A set right operand written as repeated values** — `due2-repeated-right-operand` (the list and the repeated form side by side, with the same three verdicts; `due2-profiles.md` §4, `decisions/0013`).
- **A higher layer rebinding an operand's source** — `due2-rebound-pay-amount` (the policy reads `odrl:payAmount` from the request and keeps the baseline's range; `due2-profiles.md` §2, `decisions/0014`).
- **Concept-scheme operands** — `due2-concept-purpose` (`eq` under `skos:broader`, with the SOTW supplying a concept's edges), `due2-concept-purpose-prohibition` (a prohibition, with `skos:narrower`, `skos:topConceptOf`, and `skos:hasTopConcept`), and `due2-concept-complement` (`neq` and `isNoneOf`); an in-scheme miss is `f`, and a concept in no scheme or a string is `u` (`due2-profiles.md` §4, `decisions/0015`).
- **Negative cases** — `expected_rejection` in the case format; `force-01` … `force-07` (`MissingAction`, `MissingTarget`), `due2-witness-outside-duty` (`WitnessOutsideDuty`), `oval-untyped-datetime` (`OperatorTypeMismatch`), `due2-malformed-right-operand` (`MalformedConstraint`), `due2-retyped-operand` (`RetypedOperand`), `due2-operand-range-mismatch` (`OperandRangeMismatch`), `due2-concept-out-of-scheme-right` and `due2-concept-operator` (`OperatorTypeMismatch`), `due2-concept-datatype-range` (`InvalidBinding`), `due2-empty-right-operand`, `due2-empty-logical-constraint`, `due2-repeated-member-node`, and `due2-xone-repeated-leaf` (`MalformedConstraint`), `due2-undeclared-action` and `due2-undeclared-cc-action` (`UndeclaredProfile`), `oval-refinement-on-duty`, `oval-refinement-on-policy`, `oval-constraint-on-action`, and `oval-constraint-on-collection` (`MisplacedConstraint`), `due2-policy-constraint` (`UnsupportedConstruct`), and `oval-prohibition-in-permission`, `oval-remedy-on-duty`, and `oval-consequence-on-permission` (`InvalidNesting`), `due2-replaced-policy` (`ReplacedPolicy`), `due2-unrecognised-profile` (`UnrecognisedProfile`), `due2-datetime-no-timezone`, `due2-date-with-timezone`, and `due2-eq-over-set` (`OperatorTypeMismatch`), `due2-deadline-no-timezone` (`InvalidTiming`), `due2-mixed-duration` (`MixedDuration`), `due2-literal-party` and `due2-literal-bearer` (`LiteralEntity`), `due2-and-or` (`MalformedConstraint`), `due2-two-right-operand-references` (`UnsupportedConstruct`), `due2-action-without-parent`, `due2-action-two-parents`, and `due2-action-without-value` (`InvalidActionHierarchy`), `due2-has-policy` (`MissingTarget`, `UnsupportedConstruct`), and `due2-assigner-of` and `due2-assignee-of` (`UnsupportedConstruct`).
- **An anonymous target** — `due2-anonymous-target` (a blank-node collection described only by `dct:type`: `NotApplicable` when the request names a target, `Indeterminate` when it names none; the `AnonymousEntity` warning, #79).

Open gaps:

- **Rejection codes without a negative case.** Covered: `MissingAction`, `MissingTarget`, `WitnessOutsideDuty`, `OperatorTypeMismatch` (a right operand outside its range, a right operand outside its operand's concept schemes, an operator other than `eq`, `neq`, `isAnyOf`, and `isNoneOf` on a concept-scheme operand, a `dateTime` right operand without a timezone, a `date` right operand with one, and an operator of one left value over a set-valued operand, by `eq`, which shares its rule with the other eight; the operator-not-allowed form lacks one), `MalformedConstraint` (several values on `eq`, a list mixed with a value, the empty list as a right operand, a connective over the empty list, a list that names a node twice, an `xone` that states a leaf twice, and a logical constraint with two operand properties; the missing-operand and two-lists forms lack one), `RetypedOperand` (a restated range; the cardinality and allowed-operator forms lack one), `OperandRangeMismatch`, `InvalidBinding` (a concept scheme on a datatype range; the source, property, and context-property forms lack one), `UndeclaredProfile` (an action no vocabulary defines; an undeclared DPROD or due2 namespace lacks one), `MisplacedConstraint` (a refinement on a Duty and on a Policy, a constraint on an action node and on an AssetCollection; a constraint on an Asset or a Party lacks one), `UnsupportedConstruct` (a constraint on the Policy, `odrl:rightOperandReference`, `odrl:hasPolicy`, `odrl:assignerOf`, and `odrl:assigneeOf`; `odrl:inheritFrom`, `odrl:implies`, a misplaced `odrl:source`, and a collection refinement lack one), `InvalidNesting` (a Prohibition under a Permission, a remedy on a Duty, a consequence on a Permission; a consequence on a Consequence or a Remedy, and a node in two Rule classes, lack one), `ReplacedPolicy`, `UnrecognisedProfile`, `InvalidTiming` (a deadline `dateTime` without a timezone; the two-deadline, non-RRULE, and neither-`dateTime`-nor-`duration` forms lack one), `MixedDuration` (a right operand; the deadline form lacks one), `LiteralEntity` (a literal assigner and assignee, and a literal in a profile's own party role, `dprod:subjectOfDuty`; a literal target and output lack one), `InvalidActionHierarchy` (an action with no `odrl:includedIn`, one with two, and a blank action node without `rdf:value`; a parent that is not an Action, and a cycle that reaches neither `odrl:use` nor `odrl:transfer`, lack one). `ConflictingProfileDeclaration` cannot have one while DPROD is the only profile that ships a binding module, because it needs two modules that declare one term differently; the clingo-i unit tests cover it with test modules. Every other error of `due2-diagnostics.md` §3 needs one. `odrl-compound-to-atomic-normalization.md` §10's minimum suite names the stage-1 vectors. The *unchecked* rows need W1 itself, because the checker cannot see them.
- **`admit_source` / `admit_age`** — a case-format gap: `sotw.facts` carries no attribution (`source`, `observed_at`), so the filter cannot be shown at work; three cases note this in `notes`. Fixing it needs a fact-attribution extension to the case format.
- **Declared preference** — the incomparable frontier has a case (`due2-incomparable-frontier`), but the preference format is open (`due2-workflows.md` §9 #3, #5).
- **Several policies per case** — `due2-workflows.md` §9 #7 (#1); blocked on a case-format extension. With it come the cross-policy combinations: every case's `combination` is `prohibit-overrides`.
- **`frontier_complete`** — no case asserts it, neither an incomplete frontier under a definite `Pending` nor the beyond-`max_frontier_vars` fallback (`due2-workflows.md` §6.4, `decisions/0004`); needs `expected.frontier_complete` in the case format (#30).
- **The explanation in the rest of the corpus** — 80 of 457 scenarios assert `verdict_basis` and `eliminated`, and 52 assert `unknown_parts` (`due2-workflows.md` §3.7). The W3 done-gate names `verdict_basis` (`correctness-strategy.md` §4.5), so the rest are backfilled as cases are touched. An elimination by the cross-policy `combination` waits for several policies per case. 25 of the 90 `Indeterminate` scenarios assert `verdict_range`. The `Indeterminate` witness is open (#58).
- **`hasPart` and `isA` with a list**, and a non-trivial `partOf` closure under a list — `due2-profiles.md` §4, `decisions/0005` (#32).
- **Remedies and consequences** — carried by stage 1, not evaluated for access; no case until the monitoring question (`due2-workflows.md` §9 #4, #6) is specified. OVAL's monitoring cases are the external material.
